// kwin-shot — captures the whole KWin workspace to a PNG through org.kde.KWin.ScreenShot2.
// Used by the test harness (headless KWin and the VM). Usage: kwin-shot out.png
#include <QCoreApplication>
#include <QDBusConnection>
#include <QDBusMessage>
#include <QDBusArgument>
#include <QDBusMetaType>
#include <QDBusUnixFileDescriptor>
#include <QImage>
#include <QVariantMap>
#include <unistd.h>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    if (argc < 2) { fprintf(stderr, "usage: kwin-shot out.png\n"); return 2; }
    int fds[2];
    if (pipe(fds) != 0) return 1;

    QDBusMessage msg = QDBusMessage::createMethodCall(QStringLiteral("org.kde.KWin"), QStringLiteral("/org/kde/KWin/ScreenShot2"),
                                                      QStringLiteral("org.kde.KWin.ScreenShot2"), QStringLiteral("CaptureWorkspace"));
    QVariantMap options{{QStringLiteral("include-cursor"), false}, {QStringLiteral("native-resolution"), true}};
    msg << options << QVariant::fromValue(QDBusUnixFileDescriptor(fds[1]));
    const QDBusMessage reply = QDBusConnection::sessionBus().call(msg, QDBus::Block, 20000);
    ::close(fds[1]);
    if (reply.type() != QDBusMessage::ReplyMessage) {
        fprintf(stderr, "kwin-shot: %s\n", qPrintable(reply.errorMessage()));
        return 1;
    }
    const QVariantMap r = qdbus_cast<QVariantMap>(reply.arguments().value(0));
    const int w = r.value(QStringLiteral("width")).toInt(), h = r.value(QStringLiteral("height")).toInt();
    const int stride = r.value(QStringLiteral("stride")).toInt();
    const auto format = QImage::Format(r.value(QStringLiteral("format")).toInt());
    QByteArray data;
    data.resize(qsizetype(stride) * h);
    qsizetype got = 0;
    while (got < data.size()) {
        const ssize_t n = ::read(fds[0], data.data() + got, data.size() - got);
        if (n <= 0) break;
        got += n;
    }
    ::close(fds[0]);
    if (got != data.size()) { fprintf(stderr, "kwin-shot: short read %lld/%lld\n", (long long)got, (long long)data.size()); return 1; }
    const QImage img(reinterpret_cast<const uchar *>(data.constData()), w, h, stride, format);
    if (!img.copy().save(QString::fromLocal8Bit(argv[1]))) return 1;
    printf("%s %dx%d\n", argv[1], w, h);
    return 0;
}
