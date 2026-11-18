# Droplet Shell — DROPLET AURA desktop shell (Wayland / KWin), Droplet OS 0.2
cmake_minimum_required(VERSION 3.25)
project(droplet-shell VERSION 0.2.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(ECM 6.0 REQUIRED NO_MODULE)
list(APPEND CMAKE_MODULE_PATH ${ECM_MODULE_PATH})
include(KDEInstallDirs)

find_package(Qt6 6.8 REQUIRED COMPONENTS Core Gui Quick Qml DBus)
find_package(KF6 6.0 REQUIRED COMPONENTS WindowSystem GlobalAccel Service KIO CoreAddons Config)

qt_standard_project_setup(REQUIRES 6.8)

qt_add_executable(droplet-shell src/main.cpp)

set_source_files_properties(qml/Theme.qml PROPERTIES QT_QML_SINGLETON_TYPE TRUE)

qt_add_qml_module(droplet-shell
    URI Droplet
    VERSION 1.0
    SOURCES
        src/effects.h src/effects.cpp
        src/apps.h src/apps.cpp
        src/system.h src/system.cpp
        src/notifications.h src/notifications.cpp
        src/shell.h src/shell.cpp
    QML_FILES
        qml/Main.qml qml/Theme.qml qml/Glass.qml qml/Symbol.qml
        qml/Wallpaper.qml qml/Sky.qml qml/MenuBar.qml qml/DropletMenu.qml qml/AppMenu.qml
        qml/Dock.qml qml/Launcher.qml qml/ControlCenter.qml qml/Notifications.qml
        qml/Widgets.qml qml/About.qml qml/Toggle.qml qml/Slider.qml qml/MenuItem.qml
        qml/Ressort.qml qml/Teinte.qml qml/Pression.qml
    RESOURCES
        assets/eclipse.svg
)

target_link_libraries(droplet-shell PRIVATE
    Qt6::Quick Qt6::Qml Qt6::DBus
    KF6::WindowSystem KF6::GlobalAccel KF6::Service KF6::KIOGui KF6::CoreAddons KF6::ConfigCore)

install(TARGETS droplet-shell RUNTIME DESTINATION ${KDE_INSTALL_BINDIR})
target_include_directories(droplet-shell PRIVATE src)
target_compile_definitions(droplet-shell PRIVATE PROJECT_VERSION_STRING="${PROJECT_VERSION}")

set(AURA ${CMAKE_CURRENT_SOURCE_DIR}/../../aura)
install(DIRECTORY ${AURA}/icons/ DESTINATION ${KDE_INSTALL_DATADIR}/droplet/icons)
install(DIRECTORY ${AURA}/symbols/ DESTINATION ${KDE_INSTALL_DATADIR}/droplet/symbols)
install(DIRECTORY ${AURA}/wallpapers/ DESTINATION ${KDE_INSTALL_DATADIR}/droplet/wallpapers)
install(FILES org.droplet.shell.desktop DESTINATION ${KDE_INSTALL_APPDIR})
