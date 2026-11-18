/*
    Droplet Liquid Glass — KWin 6 effect.

    Replaces KWin's blur effect: it owns the org_kde_kwin_blur protocol (KWindowEffects /
    enableBlurBehind), reads every surface's blur region, splits it back into the rounded
    shapes the client asked for, and paints each one with liquidglass.frag: lensing at the
    rim, chromatic dispersion, light frost, adaptive tint, specular light and a contact shadow.
    Surfaces of the Droplet shell get the full material; other applications that ask for a
    blur get a plain frost (no lens, no light), like the stock effect.

    SPDX-License-Identifier: GPL-2.0-or-later
*/

#include "core/rendertarget.h"
#include "core/renderviewport.h"
#include "effect/effect.h"
#include "effect/effecthandler.h"
#include "effect/effectwindow.h"
#include "opengl/eglcontext.h"
#include "opengl/glframebuffer.h"
#include "opengl/glshader.h"
#include "opengl/glshadermanager.h"
#include "opengl/gltexture.h"
#include "opengl/glvertexbuffer.h"
#include "scene/backgroundeffectitem.h"
#include "scene/windowitem.h"
#include "wayland/blur.h"
#include "wayland/display.h"
#include "wayland/surface.h"

#include <KConfigGroup>
#include <KConfigWatcher>
#include <KSharedConfig>

#include <QFile>
#include <QLoggingCategory>
#include <QTimer>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <map>
#include <QSet>
#include <unordered_map>

Q_LOGGING_CATEGORY(DROPLET_GLASS, "kwin_effect_dropletglass", QtWarningMsg)

static void ensureResources()
{
    Q_INIT_RESOURCE(dropletglass);
}

namespace KWin
{

struct Material {
    float bevel, refraction, dispersion, frost;
    QVector3D tint;
    float tintAmount, saturation, brightness, specular, shadowAlpha, shadowBlur, shadowY;
    float lumaTarget = 0, lumaAmount = 0, rimDark = 0, edgeGlow = 0;
};

// Size-adaptive material measured on the Apple macOS 27 kit (pages Materials and Liquid Glass):
// frost 6 for small controls, 16 for panels and the Dock, 25 for menus and large popups; shadow
// 0/+18/48 at 25 % (light) or 45 % (dark) for panels, almost nothing under small controls; dark
// glass is a Luminosity blend toward #1a1a1a, light glass a 60 % white Lighten.
// Must stay identical to GlassGL.material() in aura/render/glassgl.py (the offline prototype).
static Material materialFor(bool dark, float w, float h)
{
    const float md = std::min(w, h);
    const float s = std::clamp((md - 44.0f) / 56.0f, 0.0f, 1.0f);   // 0 = small control, 1 = panel
    const float big = std::clamp((md - 100.0f) / 80.0f, 0.0f, 1.0f); // menus, launcher
    auto mix = [](float a, float b, float k) { return a + (b - a) * k; };
    Material m{};
    m.bevel = mix(10, 18, s);
    m.refraction = 7;
    m.dispersion = 0.35f;
    m.frost = 6 + 10 * s + 9 * big;
    m.shadowBlur = mix(10, 40, s);
    m.shadowY = mix(3, 14, s);
    if (dark) {
        m.tint = {0.10f, 0.10f, 0.10f};
        m.tintAmount = 0;
        m.saturation = 1.35f;
        m.specular = 0.75f;
        m.shadowAlpha = mix(0.12f, 0.40f, s);
        m.lumaTarget = 0.10f;
        m.lumaAmount = mix(0.55f, 0.75f, s);
        m.edgeGlow = 0.06f;
    } else {
        m.tint = {1, 1, 1};
        m.tintAmount = mix(0.42f, 0.62f, s);
        m.saturation = 1.25f;
        m.specular = 0.85f;
        m.shadowAlpha = mix(0.06f, 0.22f, s);
        m.rimDark = 0.10f;
        m.edgeGlow = 0.05f;
    }
    return m;
}
// windows that ask for plain blur (not the Droplet shell) get a frost without lens or light
static const Material kFrost{1, 0, 0.0f, 10.0f, {0, 0, 0}, 0.0f, 1.4f, 0.0f, 0.0f, 0.0f, 1, 0};

struct Shape {
    QRect rect;      // window-local, logical
    float radius;
    // presence animation: glass materialises when a shape appears and dissolves when it goes,
    // with the same timing as the shell's content (Theme "vif" in, "sortie" out)
    int dir = 0;                        // +1 appearing, -1 leaving, 0 settled
    qint64 start = 0;                   // ms, steady clock
    float from = 1;                     // presence when the current animation started
};

static qint64 nowMs()
{
    return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

// Theme.vif: spring, response 0.28 s, damping 0.86 (aura/render/motion.py)
static float springVif(float t)
{
    const float w0 = 2.0f * float(M_PI) / 0.28f, z = 0.86f;
    const float wd = w0 * std::sqrt(1 - z * z), a = z * w0;
    return 1 - std::exp(-a * t) * (std::cos(wd * t) + a / wd * std::sin(wd * t));
}

// Theme.sortie: cubic Bezier (0.30, 0, 0.80, 0.15), 200 ms
static float easeSortie(float u)
{
    const float x1 = 0.30f, y1 = 0.0f, x2 = 0.80f, y2 = 0.15f;
    float s = u;
    for (int i = 0; i < 8; ++i) {   // Newton on x(s) = u
        const float m = 1 - s;
        const float x = 3 * m * m * s * x1 + 3 * m * s * s * x2 + s * s * s;
        const float dx = 3 * m * m * x1 + 6 * m * s * (x2 - x1) + 3 * s * s * (1 - x2);
        if (std::abs(dx) < 1e-5f) break;
        s = std::clamp(s - (x - u) / dx, 0.0f, 1.0f);
    }
    const float m = 1 - s;
    return 3 * m * m * s * y1 + 3 * m * s * s * y2 + s * s * s;
}

static constexpr qint64 kAppearMs = 311, kLeaveMs = 200;

// current presence of a shape (1 = fully there)
static float presenceOf(const Shape &s, qint64 now)
{
    if (s.dir == 0) return 1;
    const float t = float(now - s.start);
    if (s.dir > 0) {
        if (t >= kAppearMs) return 1;
        return s.from + (1 - s.from) * std::clamp(springVif(t / 1000.0f), 0.0f, 1.0f);
    }
    if (t >= kLeaveMs) return 0;
    return s.from * (1 - easeSortie(t / float(kLeaveMs)));
}

struct RenderData {
    std::unique_ptr<GLTexture> texture;
    std::unique_ptr<GLFramebuffer> framebuffer;
    bool mipsStale = true;
};

struct WindowData {
    QList<Shape> shapes;
    bool droplet = false;
    std::unique_ptr<BackgroundEffectItem> item;
    std::unordered_map<RenderView *, RenderData> render;
};

class DropletGlassEffect : public Effect
{
    Q_OBJECT

public:
    DropletGlassEffect();
    ~DropletGlassEffect() override;

    static bool supported() { return effects->isOpenGLCompositing(); }
    static bool enabledByDefault() { return true; }

    void reconfigure(ReconfigureFlags flags) override;
    void prePaintScreen(ScreenPrePaintData &data, std::chrono::milliseconds presentTime) override;
    void postPaintScreen() override;
    void drawWindow(const RenderTarget &renderTarget, const RenderViewport &viewport, EffectWindow *w, int mask,
                    const Region &deviceRegion, WindowPaintData &data) override;
    bool isActive() const override { return m_valid && !effects->isScreenLocked(); }
    bool blocksDirectScanout() const override { return false; }
    int requestedEffectChainPosition() const override { return 20; }   // where the blur effect sits

private:
    void windowAdded(EffectWindow *w);
    void windowDeleted(EffectWindow *w);
    void update(EffectWindow *w);
    static QList<Shape> shapesFromRegion(const Region &region);
    void setUniforms(const Material &m, const QRectF &shape, float radius, const QRectF &cap, float presence);

    void noteDamage(EffectWindow *w) { m_pendingDamage.insert(w); }
    void noteStructure() { m_pendingStructural = true; }
    bool backgroundChanged(EffectWindow *w, const QRect &cap) const;

    // what changed on screen since the last frame: glass only re-reads the pixels behind it when
    // something *below* it changed (its own content changing does not change what is behind it)
    QSet<EffectWindow *> m_pendingDamage, m_frameDamage;
    bool m_pendingStructural = true, m_frameStructural = true;

    std::unique_ptr<GLShader> m_shader;
    std::map<EffectWindow *, WindowData> m_windows;
    std::map<EffectWindow *, QMetaObject::Connection> m_connections;
    RenderView *m_view = nullptr;
    bool m_valid = false;
    bool m_dark = true;
    float m_maxLod = 4;
    int m_debugView = 0;
    bool m_mipWarned = false;
    KConfigWatcher::Ptr m_watcher;

    static BlurManagerInterface *s_manager;
    static QTimer *s_removeTimer;
};

BlurManagerInterface *DropletGlassEffect::s_manager = nullptr;
QTimer *DropletGlassEffect::s_removeTimer = nullptr;

DropletGlassEffect::DropletGlassEffect()
{
    ensureResources();
    QFile f(QStringLiteral(":/effects/dropletglass/liquidglass.frag"));
    if (!f.open(QIODevice::ReadOnly)) {
        qCWarning(DROPLET_GLASS) << "shader missing";
        return;
    }
    QByteArray frag = f.readAll();
    // drop the file's own "#version" line (it is not the first line: a comment header precedes it)
    {
        const qsizetype v = frag.indexOf("#version");
        if (v >= 0) frag.remove(v, frag.indexOf('\n', v) - v);
    }
    const bool gles = EglContext::currentContext() && EglContext::currentContext()->isOpenGLES();
    // ShaderManager binds the attributes "vertex" / "texCoord" and the output "fragColor"
    const QByteArray header = gles ? QByteArrayLiteral("#version 300 es\nprecision highp float;\n#define KWIN 1\n#define frag fragColor\n")
                                   : QByteArrayLiteral("#version 140\n#define KWIN 1\n#define frag fragColor\n");
    const QByteArray vert = header + R"(
uniform mat4 modelViewProjectionMatrix;
in vec2 vertex;
in vec2 texCoord;
out vec2 lpos;
void main() {
    gl_Position = modelViewProjectionMatrix * vec4(vertex, 0.0, 1.0);
    lpos = texCoord;
}
)";
    m_shader = ShaderManager::instance()->loadShaderFromCode(vert, header + frag);
    if (!m_shader || !m_shader->isValid()) {
        qCWarning(DROPLET_GLASS) << "failed to compile liquidglass.frag";
        return;
    }

    // own the blur protocol (the stock blur effect is disabled in the Droplet session)
    if (!s_removeTimer) {
        s_removeTimer = new QTimer(QCoreApplication::instance());
        s_removeTimer->setSingleShot(true);
        s_removeTimer->callOnTimeout([] {
            s_manager->remove();
            s_manager = nullptr;
        });
    }
    s_removeTimer->stop();
    if (!s_manager) {
        s_manager = new BlurManagerInterface(effects->waylandDisplay(), s_removeTimer);
    }

    m_watcher = KConfigWatcher::create(KSharedConfig::openConfig(QStringLiteral("kdeglobals")));
    connect(m_watcher.data(), &KConfigWatcher::configChanged, this, [this](const KConfigGroup &g) {
        if (g.name() == QLatin1String("General")) {
            reconfigure(ReconfigureAll);
        }
    });

    connect(effects, &EffectsHandler::windowAdded, this, &DropletGlassEffect::windowAdded);
    connect(effects, &EffectsHandler::windowDeleted, this, &DropletGlassEffect::windowDeleted);
    connect(effects, &EffectsHandler::stackingOrderChanged, this, &DropletGlassEffect::noteStructure);
    connect(effects, &EffectsHandler::desktopChanged, this, &DropletGlassEffect::noteStructure);
    connect(effects, &EffectsHandler::viewRemoved, this, [this](RenderView *view) {
        for (auto &[w, d] : m_windows) {
            d.render.erase(view);
        }
    });
    for (EffectWindow *w : effects->stackingOrder()) {
        windowAdded(w);
    }
    reconfigure(ReconfigureAll);
    m_valid = true;
}

DropletGlassEffect::~DropletGlassEffect()
{
    if (s_manager) {
        s_removeTimer->start(1000);
    }
}

void DropletGlassEffect::reconfigure(ReconfigureFlags)
{
    KSharedConfig::openConfig(QStringLiteral("kdeglobals"))->reparseConfiguration();
    const KConfigGroup g(KSharedConfig::openConfig(QStringLiteral("kdeglobals")), QStringLiteral("General"));
    m_dark = g.readEntry("ColorScheme", QStringLiteral("DropletSombre")) != QLatin1String("DropletClair");
    // deepest mip level the frost may read (diagnostics / drivers with broken mip chains)
    const KConfigGroup e(effects->config(), QStringLiteral("Effect-dropletglass"));
    m_maxLod = std::clamp(e.readEntry("MaxLod", 4.0), 0.0, 4.0);
    m_debugView = e.readEntry("DebugView", 0);
    qCDebug(DROPLET_GLASS) << "dark" << m_dark << "maxLod" << m_maxLod << "debugView" << m_debugView;
    effects->addRepaintFull();
}

void DropletGlassEffect::windowAdded(EffectWindow *w)
{
    noteStructure();
    connect(w, &EffectWindow::windowDamaged, this, &DropletGlassEffect::noteDamage);
    connect(w, &EffectWindow::windowFrameGeometryChanged, this, &DropletGlassEffect::noteStructure);
    connect(w, &EffectWindow::windowExpandedGeometryChanged, this, &DropletGlassEffect::noteStructure);
    connect(w, &EffectWindow::minimizedChanged, this, &DropletGlassEffect::noteStructure);
    connect(w, &EffectWindow::windowHiddenChanged, this, &DropletGlassEffect::noteStructure);
    connect(w, &EffectWindow::windowOpacityChanged, this, &DropletGlassEffect::noteStructure);
    if (SurfaceInterface *surface = w->surface()) {
        m_connections[w] = connect(surface, &SurfaceInterface::blurChanged, this, [this, w] {
            update(w);
        });
    }
    update(w);
}

void DropletGlassEffect::windowDeleted(EffectWindow *w)
{
    noteStructure();
    m_pendingDamage.remove(w);
    m_frameDamage.remove(w);
    if (auto it = m_windows.find(w); it != m_windows.end()) {
        effects->makeOpenGLContextCurrent();
        m_windows.erase(it);
    }
    if (auto it = m_connections.find(w); it != m_connections.end()) {
        disconnect(it->second);
        m_connections.erase(it);
    }
}

// The client sends a union of rounded rectangles (Effects::glass in the shell builds it from two
// crossing bands and four corner discs). Group the region's rects into connected shapes and read
// the corner radius back from how much the top row is inset.
QList<Shape> DropletGlassEffect::shapesFromRegion(const Region &region)
{
    QList<QRect> rects;
    for (const Rect &r : region.rects()) {
        rects.append(QRect(r));
    }
    const int n = rects.size();
    std::vector<int> parent(n);
    for (int i = 0; i < n; ++i) parent[i] = i;
    std::function<int(int)> find = [&](int i) { return parent[i] == i ? i : parent[i] = find(parent[i]); };
    for (int i = 0; i < n; ++i) {
        const QRect a = rects[i].adjusted(-1, -1, 1, 1);
        for (int j = i + 1; j < n; ++j) {
            if (a.intersects(rects[j])) parent[find(i)] = find(j);
        }
    }
    std::map<int, QList<QRect>> groups;
    for (int i = 0; i < n; ++i) groups[find(i)].append(rects[i]);

    QList<Shape> shapes;
    for (const auto &[root, list] : groups) {
        QRect box;
        for (const QRect &r : list) box |= r;
        int left = box.right(), right = box.left();
        for (const QRect &r : list) {
            if (r.top() == box.top()) {
                left = std::min(left, r.left());
                right = std::max(right, r.right());
            }
        }
        // a disc of radius R cut by the first pixel row leaves an inset i = R - sqrt(R - 1/4):
        // solve for R (s = sqrt(R): s^2 - s = i)
        const float inset = std::max(0, std::min(left - box.left(), box.right() - right));
        const float sq = (1.0f + std::sqrt(1.0f + 4.0f * inset)) / 2.0f;
        float radius = std::min<float>(inset > 0 ? sq * sq : 0, std::min(box.width(), box.height()) / 2.0f);
        if (radius < 2) radius = 0;
        shapes.append({box, radius});
    }
    return shapes;
}

void DropletGlassEffect::update(EffectWindow *w)
{
    std::optional<Region> content;
    if (SurfaceInterface *surface = w->surface()) {
        if (surface->blur()) {
            content = surface->blur()->region();
        }
    }
    const QRect contents = w->contentsRect().toRect();
    QList<Shape> shapes;
    if (!content.has_value()) {
        auto it = m_windows.find(w);
        if (it == m_windows.end()) return;
        if (!it->second.droplet) {
            effects->makeOpenGLContextCurrent();
            m_windows.erase(it);
            return;
        }
        // a Droplet surface dropped its glass: let the shapes dissolve (handled below)
    } else if (content->isEmpty()) {
        shapes = {Shape{QRect(QPoint(0, 0), contents.size()), 0}};
    } else {
        shapes = shapesFromRegion(*content);
    }
    for (Shape &s : shapes) {
        s.rect.translate(contents.topLeft());
    }
    WindowData &d = m_windows[w];
    const bool droplet = w->windowClass().contains(QLatin1String("droplet"), Qt::CaseInsensitive);
    if (droplet) {
        // carry the presence animation across updates: a shape that only moved or resized (it is
        // re-sent every frame while the shell animates it) is the same shape
        const qint64 now = nowMs();
        const auto overlap = [](const QRect &a, const QRect &b) {
            const QRect i = a & b;
            const double small = std::min<double>(double(a.width()) * a.height(), double(b.width()) * b.height());
            return small > 0 ? double(i.width()) * i.height() / small : 0.0;
        };
        std::vector<bool> used(d.shapes.size(), false);
        for (Shape &n : shapes) {
            int best = -1;
            double bestOv = 0.6;
            for (qsizetype i = 0; i < d.shapes.size(); ++i) {
                if (used[i]) continue;
                const double ov = overlap(n.rect, d.shapes[i].rect);
                if (ov > bestOv) { bestOv = ov; best = int(i); }
            }
            if (best >= 0) {
                used[best] = true;
                const Shape &o = d.shapes[best];
                if (o.dir < 0) {          // was dissolving: come back from where it is
                    n.from = presenceOf(o, now); n.dir = 1; n.start = now;
                } else {
                    n.dir = o.dir; n.start = o.start; n.from = o.from;
                }
            } else {
                n.dir = 1; n.start = now; n.from = 0;
            }
        }
        for (qsizetype i = 0; i < d.shapes.size(); ++i) {
            if (used[i]) continue;
            Shape g = d.shapes[i];
            const float p = presenceOf(g, now);
            if (p <= 0.002f) continue;
            if (g.dir >= 0) { g.from = p; g.dir = -1; g.start = now; }
            shapes.append(g);
        }
        if (!content.has_value() && shapes.isEmpty()) {
            effects->makeOpenGLContextCurrent();
            m_windows.erase(w);
            return;
        }
    }
    // clients re-send the same region often (every Effects.glass call): only a real change
    // costs a repaint, and only of the area that changed
    const auto same = [](const QList<Shape> &a, const QList<Shape> &b) {
        if (a.size() != b.size()) return false;
        for (qsizetype i = 0; i < a.size(); ++i)
            if (a[i].rect != b[i].rect || !qFuzzyCompare(a[i].radius + 1, b[i].radius + 1)) return false;
        return true;
    };
    const bool changed = !same(shapes, d.shapes);
    QRect old;
    for (const Shape &s : d.shapes) old |= s.rect;
    d.shapes = shapes;
    d.droplet = droplet;
    if (!d.item) {
        d.item = std::make_unique<BackgroundEffectItem>(w->windowItem());
    }
    QRect bounds;
    for (const Shape &s : d.shapes) bounds |= s.rect;
    const int margin = d.droplet ? 60 : 16;   // lens + frost 25 + shadow (40 blur + 14 offset)
    d.item->setPixelsToExpandRepaintsBelowOpaqueRegions(margin);
    d.item->setEffectBoundingRect(QRectF(bounds.adjusted(-margin, -margin, margin, margin)));
    if (changed) {
        const QPoint origin = w->pos().toPoint();
        effects->addRepaint((old | bounds).translated(origin).adjusted(-margin, -margin, margin, margin));
    }
}

void DropletGlassEffect::postPaintScreen()
{
    // keep painting while a shape materialises or dissolves; drop the ghosts that are gone
    const qint64 now = nowMs();
    for (auto it = m_windows.begin(); it != m_windows.end();) {
        WindowData &d = it->second;
        QRect area;
        for (Shape &s : d.shapes) {
            if (s.dir == 0) continue;
            area |= s.rect;
            if (s.dir > 0 && now - s.start >= kAppearMs) { s.dir = 0; s.from = 1; }
        }
        d.shapes.removeIf([now](const Shape &s) { return s.dir < 0 && now - s.start >= kLeaveMs; });
        if (!area.isEmpty()) {
            const QPoint origin = it->first->pos().toPoint();
            effects->addRepaint(area.translated(origin).adjusted(-60, -60, 60, 60));
        }
        ++it;
    }
    effects->postPaintScreen();
}

void DropletGlassEffect::prePaintScreen(ScreenPrePaintData &data, std::chrono::milliseconds presentTime)
{
    m_view = data.view;
    m_frameDamage = std::exchange(m_pendingDamage, {});
    m_frameStructural = std::exchange(m_pendingStructural, false);
    effects->prePaintScreen(data, presentTime);
}

bool DropletGlassEffect::backgroundChanged(EffectWindow *w, const QRect &cap) const
{
    if (m_frameStructural || effects->activeFullScreenEffect())
        return true;
    if (m_frameDamage.isEmpty())
        return false;
    const QList<EffectWindow *> order = effects->stackingOrder();
    const qsizetype self = order.indexOf(w);
    for (EffectWindow *o : m_frameDamage) {
        if (o == w) continue;
        const qsizetype i = order.indexOf(o);
        if (i < 0 || i > self) continue;                    // above us: not behind the glass
        if (o->expandedGeometry().toAlignedRect().intersects(cap)) return true;
    }
    return false;
}

void DropletGlassEffect::setUniforms(const Material &m, const QRectF &shape, float radius, const QRectF &cap, float presence)
{
    GLShader *s = m_shader.get();
    s->setUniform("presence", presence);
    s->setUniform("bg", 0);
    s->setUniform("res", QVector2D(cap.width(), cap.height()));
    s->setUniform("capRect", QVector4D(cap.x(), cap.y(), cap.width(), cap.height()));
    s->setUniform("rect", QVector4D(shape.x(), shape.y(), shape.width(), shape.height()));
    s->setUniform("radius", radius);
    s->setUniform("bevel", std::min<float>(m.bevel, std::max(radius, 1.0f)));
    s->setUniform("refraction", m.refraction);
    s->setUniform("dispersion", m.dispersion);
    s->setUniform("frost", m.frost);
    s->setUniform("tintColor", m.tint);
    s->setUniform("tintAmount", m.tintAmount);
    s->setUniform("saturation", m.saturation);
    s->setUniform("brightness", m.brightness);
    s->setUniform("lightDir", QVector2D(-0.3f, -0.95f).normalized());
    s->setUniform("lumaTarget", m.lumaTarget);
    s->setUniform("lumaAmount", m.lumaAmount);
    s->setUniform("rimDark", m.rimDark);
    s->setUniform("edgeGlow", m.edgeGlow);
    s->setUniform("maxLod", m_maxLod);
    s->setUniform("debugView", m_debugView);
    s->setUniform("specular", m.specular);
    s->setUniform("shadowAlpha", m.shadowAlpha);
    s->setUniform("shadowBlur", m.shadowBlur);
    s->setUniform("shadowY", m.shadowY);
}

void DropletGlassEffect::drawWindow(const RenderTarget &renderTarget, const RenderViewport &viewport, EffectWindow *w,
                                    int mask, const Region &deviceRegion, WindowPaintData &data)
{
    auto it = m_windows.find(w);
    const bool transformed = (mask & PAINT_WINDOW_TRANSFORMED) || data.xTranslation() || data.yTranslation()
        || !qFuzzyCompare(data.xScale(), 1.0) || !qFuzzyCompare(data.yScale(), 1.0);
    if (it == m_windows.end() || it->second.shapes.isEmpty() || transformed || effects->activeFullScreenEffect()) {
        effects->drawWindow(renderTarget, viewport, w, mask, deviceRegion, data);
        return;
    }
    WindowData &d = it->second;
    const QPoint origin = w->pos().toPoint();

    // 1. the background behind every shape (+ margin for the lens, the frost and the shadow)
    QRect bounds;
    for (const Shape &s : d.shapes) bounds |= s.rect.translated(origin);
    const int margin = d.droplet ? 60 : 16;   // lens + frost 25 + shadow (40 blur + 14 offset)
    const QRect screen = viewport.renderRect().toRect();
    const QRect cap = bounds.adjusted(-margin, -margin, margin, margin) & screen;
    if (cap.isEmpty()) {
        effects->drawWindow(renderTarget, viewport, w, mask, deviceRegion, data);
        return;
    }
    GLenum format = renderTarget.texture() ? renderTarget.texture()->internalFormat() : GL_RGBA8;
    RenderData &rd = d.render[m_view];
    if (!rd.texture || rd.texture->size() != cap.size() || rd.texture->internalFormat() != format) {
        // a short mip chain: the shader frosts with 9 taps on it instead of 40 full-resolution taps
        rd.texture = GLTexture::allocate(format, cap.size(), 5);
        qCDebug(DROPLET_GLASS) << "capture texture" << cap << Qt::hex << format << "target"
                              << (renderTarget.texture() ? "texture" : "framebuffer");
        if (!rd.texture) {
            effects->drawWindow(renderTarget, viewport, w, mask, deviceRegion, data);
            return;
        }
        rd.texture->setFilter(GL_LINEAR_MIPMAP_LINEAR);
        rd.texture->setWrapMode(GL_CLAMP_TO_EDGE);
        rd.framebuffer = std::make_unique<GLFramebuffer>(rd.texture.get());
        // first use: take the whole area
        rd.framebuffer->blitFromRenderTarget(renderTarget, viewport, Rect(cap), Rect(QRect(QPoint(0, 0), cap.size())));
        rd.mipsStale = true;
    }
    // only what was repainted this frame is fresh; elsewhere the texture still holds the background
    // Reading back the frame being drawn stalls the GPU (and costs a whole frame with software
    // rendering): only do it when the background behind the glass really changed.
    bool fresh = rd.mipsStale;
    if (!fresh && backgroundChanged(w, cap)) {
        const Region dirty = viewport.mapFromDeviceCoordinatesContained(deviceRegion) & Region(Rect(cap));
        for (const Rect &r : dirty.rects()) {
            rd.framebuffer->blitFromRenderTarget(renderTarget, viewport, r, r.translated(-cap.topLeft()));
            fresh = true;
        }
    }
    if (fresh) {
        // GLTexture::generateMipmaps() is a no-op on some drivers (seen with GLES on llvmpipe/KMS:
        // levels 1..4 stayed black and the frost read black): build the chain ourselves.
        rd.texture->bind();
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_BASE_LEVEL, 0);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 4);
        glGenerateMipmap(GL_TEXTURE_2D);
        if (const GLenum err = glGetError(); err != GL_NO_ERROR && !m_mipWarned) {
            m_mipWarned = true;
            qCWarning(DROPLET_GLASS) << "glGenerateMipmap failed" << Qt::hex << err << "- frost limited to level 0";
            m_maxLod = 0;
        }
        rd.texture->unbind();
        rd.mipsStale = false;
    }

    // 2. one quad per shape (shape + shadow), clipped to what is being repainted
    GLVertexBuffer *vbo = GLVertexBuffer::streamingBuffer();
    vbo->reset();
    vbo->setAttribLayout(std::span(GLVertexBuffer::GLVertex2DLayout), sizeof(GLVertex2D));

    ShaderManager::instance()->pushShader(m_shader.get());
    m_shader->setUniform(GLShader::Mat4Uniform::ModelViewProjectionMatrix, viewport.projectionMatrix());
    rd.texture->bind();
    glEnable(GL_BLEND);
    glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA);   // premultiplied

    const qint64 now = nowMs();
    for (const Shape &s : d.shapes) {
        const float presence = d.droplet ? presenceOf(s, now) : 1.0f;
        if (presence <= 0.002f) continue;
        const QRectF shape = QRectF(s.rect.translated(origin));
        const Material mat = d.droplet ? materialFor(m_dark, shape.width(), shape.height()) : kFrost;
        const float pad = mat.shadowBlur + mat.shadowY + 2;
        const QRectF quad = shape.adjusted(-pad, -pad, pad, pad).intersected(QRectF(cap));
        const RectF deviceQuad = viewport.mapToDeviceCoordinates(RectF(quad));
        QList<QRectF> pieces;
        if (deviceRegion == Region::infinite()) {
            pieces.append(QRectF(deviceQuad));
        } else {
            for (const Rect &clip : deviceRegion.rects()) {
                const QRectF i = QRectF(deviceQuad).intersected(QRectF(QRect(clip)));
                if (!i.isEmpty()) pieces.append(i);
            }
        }
        if (pieces.isEmpty()) continue;

        auto mapped = vbo->map<GLVertex2D>(pieces.size() * 6);
        if (!mapped) break;
        auto map = *mapped;
        size_t k = 0;
        for (const QRectF &dev : pieces) {
            const QRectF log = QRectF(viewport.mapFromDeviceCoordinates(RectF(dev)));
            const QVector2D p00(dev.left(), dev.top()), p11(dev.right(), dev.bottom());
            const QVector2D p10(dev.right(), dev.top()), p01(dev.left(), dev.bottom());
            const QVector2D l00(log.left(), log.top()), l11(log.right(), log.bottom());
            const QVector2D l10(log.right(), log.top()), l01(log.left(), log.bottom());
            map[k++] = {p00, l00}; map[k++] = {p11, l11}; map[k++] = {p01, l01};
            map[k++] = {p00, l00}; map[k++] = {p10, l10}; map[k++] = {p11, l11};
        }
        vbo->unmap();
        vbo->bindArrays();
        setUniforms(mat, shape, s.radius, QRectF(cap), presence);
        vbo->draw(GL_TRIANGLES, 0, pieces.size() * 6);
        vbo->unbindArrays();
        vbo->reset();
        vbo->setAttribLayout(std::span(GLVertexBuffer::GLVertex2DLayout), sizeof(GLVertex2D));
    }
    glDisable(GL_BLEND);
    ShaderManager::instance()->popShader();

    // 3. the window itself (text, icons) on top of its glass
    effects->drawWindow(renderTarget, viewport, w, mask, deviceRegion, data);
}

} // namespace KWin

KWIN_EFFECT_FACTORY_SUPPORTED_ENABLED(KWin::DropletGlassEffect, "metadata.json",
                                      return KWin::DropletGlassEffect::supported();,
                                      return KWin::DropletGlassEffect::enabledByDefault();)

#include "dropletglass.moc"
