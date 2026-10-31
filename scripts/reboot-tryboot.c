/* One-shot Raspberry Pi firmware tryboot, used after all persistent FS are read-only. */
#define _GNU_SOURCE
#include <sys/syscall.h>
#include <unistd.h>
#include <linux/reboot.h>
#include <string.h>
#include <stdio.h>
int main(int argc, char **argv) {
 if (argc != 2 || strcmp(argv[1], "--execute") || getuid() != 0) {
  fputs("Usage as root: reboot-tryboot --execute\n", stderr); return 2;
 }
 sync();
 syscall(SYS_reboot, LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2,
         LINUX_REBOOT_CMD_RESTART2, "0 tryboot");
 perror("tryboot reboot"); return 1;
}
