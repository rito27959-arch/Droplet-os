// Ressort — a NumberAnimation driven by one of the Droplet springs (Theme: doux, vif, rebond,
// sortie, fondu). With "Réduire les animations" (kdeglobals AnimationDurationFactor = 0) every
// movement (scale, position, size) becomes immediate; fades are kept, shortened.
import QtQuick
import Droplet

NumberAnimation {
    property string caractere: "doux"
    property bool mouvement: true        // false for opacity: kept when motion is reduced
    duration: SystemControl.reduceMotion ? (mouvement ? 0 : Theme.fonduDuree) : Theme.duree(caractere)
    easing.type: Easing.BezierSpline
    easing.bezierCurve: SystemControl.reduceMotion ? Theme.fonduCourbe : Theme.courbe(caractere)
}
