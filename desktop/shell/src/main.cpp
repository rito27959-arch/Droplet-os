// Droplet Shell — entry point
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQuickWindow>

#include "apps.h"

int main(int argc, char *argv[])
{
    // Layer-shell surfaces need the Wayland platform; translucent glass needs alpha.
    qputenv("QT_WAYLAND_DISABLE_WINDOWDECORATION", "1");
    QQuickWindow::setDefaultAlphaBuffer(true);

    QGuiApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("droplet-shell"));
    app.setOrganizationName(QStringLiteral("droplet"));
    app.setApplicationVersion(QStringLiteral(PROJECT_VERSION_STRING));
    app.setDesktopFileName(QStringLiteral("org.droplet.shell"));
    app.setQuitOnLastWindowClosed(false);

    QQmlApplicationEngine engine;
    engine.addImageProvider(QStringLiteral("icon"), new ThemeIconProvider);
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed, &app, [] { QCoreApplication::exit(1); },
                     Qt::QueuedConnection);
    engine.loadFromModule("Droplet", "Main");
    return app.exec();
}
