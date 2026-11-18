// Teinte — colour cross-fade with the Droplet "fondu" curve.
import QtQuick
import Droplet

ColorAnimation {
    duration: Theme.fonduDuree
    easing.type: Easing.BezierSpline
    easing.bezierCurve: Theme.fonduCourbe
}
