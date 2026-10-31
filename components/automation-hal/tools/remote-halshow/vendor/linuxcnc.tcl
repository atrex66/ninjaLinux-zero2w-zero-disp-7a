# Remote HALShow bootstrap. Do not load local linuxcnc.so or hal.so.
package require Tk
package require msgcat
namespace eval linuxcnc {}
proc hal {args} {
    set response [_remote_hal {*}$args]
    if {[lindex $response 0] eq "error"} {error [lindex $response 1]}
    return [lindex $response 1]
}
