#!/usr/bin/python3
"""Copy the recorded source snapshot and apply the small standalone adaptations."""
import pathlib
import shutil
import sys

source, output = map(pathlib.Path, sys.argv[1:])
shutil.copytree(source, output, dirs_exist_ok=True)


def replace(path, old, new):
    p = output / path
    text = p.read_text()
    if old not in text:
        raise RuntimeError(f"Patch context missing: {path}: {old[:60]}")
    p.write_text(text.replace(old, new))


# One private IPC key space, including sampler/streamer and external modules.
# This deliberately changes binary compatibility: rebuild all clients with this SDK.
replace('src/rtapi/uspace_common.h',
        'shmget((key_t) key, (int) size, IPC_CREAT | 0600)',
        'shmget((key_t) ((unsigned int)key ^ 0x41480000U), (int) size, IPC_CREAT | 0600)')
p = output / 'src/rtapi/uspace_common.h'
s = p.read_text()
start = s.index('static int detect_env_override()')
end = s.index('\nint rtapi_is_realtime()', start)
s = s[:start] + '''/* Automation HAL selects its mode explicitly, never by LinuxCNC settings. */
static int detect_realtime() {
    const char *mode = getenv("AHAL_MODE");
    return mode && strcmp(mode, "realtime") == 0 && detect_preempt_rt();
}
''' + s[end:]
p.write_text(s)

p = output / 'src/rtapi/uspace_rtapi_app.cc'
s = p.read_text()
start = s.index('static int harden_rt()')
end = s.index('\nRtapiApp &App()', start)
s = s[:start] + '''/* No setuid executable: systemd supplies RT limits to a dedicated user. */
static RtapiApp *makeApp()
{
    const char *mode = getenv("AHAL_MODE");
    if (mode && strcmp(mode, "sim") == 0) {
        fprintf(stderr, "Automation HAL: simulation (SCHED_OTHER)\\n");
        return new Posix(SCHED_OTHER);
    }
    if (!mode || strcmp(mode, "realtime") != 0) {
        fprintf(stderr, "Automation HAL: set AHAL_MODE=sim or realtime explicitly\\n");
        exit(1);
    }
    if (!rtapi_is_realtime()) {
        fprintf(stderr, "Automation HAL: realtime mode requires PREEMPT_RT\\n");
        exit(1);
    }
    struct sched_param param = {};
    param.sched_priority = 1;
    if (sched_setscheduler(0, SCHED_FIFO, &param) < 0) {
        perror("Automation HAL: SCHED_FIFO permission");
        exit(1);
    }
    param.sched_priority = 0;
    if (sched_setscheduler(0, SCHED_OTHER, &param) < 0) {
        perror("Automation HAL: restore main scheduler");
        exit(1);
    }
    if (mlockall(MCL_CURRENT | MCL_FUTURE) < 0) {
        perror("Automation HAL: mlockall");
        exit(1);
    }
    fprintf(stderr, "Automation HAL: realtime (SCHED_FIFO)\\n");
    return new Posix(SCHED_FIFO);
}
''' + s[end:]
s = s.replace('"/.rtapi_fifo"', '"/.automation-hal.sock"')
s = s.replace('    do_load_cmd("hal_lib", vector<string>());',
              '    App(); // validate requested mode before accepting modules\n'
              '    if (do_load_cmd("hal_lib", vector<string>()) != 0) return -1;')
# Preserve the inherited root refusal but remove any accidental LinuxCNC runtime selection.
p.write_text(s)

replace('src/hal/utils/halcompile.g',
        "['src', 'etc/linuxcnc', '/etc/linuxcnc', 'share/linuxcnc']",
        "['share/automation-hal']")
replace('src/hal/utils/halcompile.g', '-I/usr/include/linuxcnc ', '')
replace('src/hal/utils/halcompile.g', '-llinuxcnchal', '-lautomationhal')
replace('src/hal/utils/halcmd_completion.h',
        '#include <editline/readline.h>\n#include <histedit.h>',
        '#ifdef HAVE_READLINE\n#include <editline/readline.h>\n#include <histedit.h>\n#endif')
replace('src/hal/utils/halcmd_main.c',
        '    halcmd_completer(fragment, sp, len, completion_callback, all);',
        '#ifdef HAVE_READLINE\n'
        '    halcmd_completer(fragment, sp, len, completion_callback, all);\n'
        '#else\n'
        '    fprintf(stderr, "This headless build has no shell completion support\\n");\n'
        '    return 1;\n'
        '#endif')
