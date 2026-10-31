#!/usr/bin/env python3
"""Apply the patch in a disposable tree and exercise its actual C function.

Usage: python3 test_irq_rotation.py /path/to/unpatched/raspberrypi-linux
The input source tree is read only. Requires patch and a native C compiler.
This is a mocked-register behavioral test, not a hardware IRQ test.
"""

import argparse
import os
from pathlib import Path
import subprocess
import tempfile


PATCH = Path(__file__).with_name(
    "0001-irqchip-bcm2836-respect-domain-isolation.patch"
)
DRIVER = Path("drivers/irqchip/irq-bcm2836.c")

PRELUDE = r"""
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
typedef uint32_t u32;
#define __iomem
#define LOCAL_GPU_ROUTING 0
enum hk_type { HK_TYPE_DOMAIN };
static u32 reg_value, active_mask, hk_mask, writes;
static struct { unsigned char *base; } intc;
bool cpu_active(u32 cpu) { return (active_mask & (1U << cpu)) != 0; }
bool housekeeping_test_cpu(int cpu, enum hk_type type)
{
    (void)type;
    return !TEST_ISOLATION_ENABLED || (hk_mask & (1U << cpu)) != 0;
}
u32 readl(void *address) { (void)address; return reg_value; }
void writel(u32 value, void *address)
{
    (void)address;
    reg_value = value;
    writes++;
}
#define CHECK(condition, message) do { \
    if (!(condition)) { \
        fprintf(stderr, "%s (active=%x housekeeping=%x result=%x)\n", \
                message, active_mask, hk_mask, reg_value); \
        exit(1); \
    } \
} while (0)
"""

TESTS = r"""
int main(void)
{
    static const u32 upper[] = {
        0, 4, 8, 12, 0xfffffff0U, 0x80000000U, 0xa5a5a5a4U, 0xfffffffcU
    };
    unsigned char register_space[4];
    unsigned int cases = 0;
    intc.base = register_space;
    /* Reproduce the observed failure: CPU1 must not hand IRQs to CPU2. */
    active_mask = 15;
    hk_mask = 3;
    reg_value = 1;
    bcm2836_arm_irqchip_spin_gpu_irq();
    if (TEST_ISOLATION_ENABLED)
        CHECK(hk_mask & (1U << (reg_value & 3)), "isolated CPU selected");
    for (active_mask = 0; active_mask < 16; active_mask++)
        for (hk_mask = 0; hk_mask < 16; hk_mask++)
            for (u32 current = 0; current < 4; current++)
                for (unsigned int b = 0; b < sizeof(upper)/sizeof(upper[0]); b++) {
                    u32 before = upper[b] | current;
                    u32 allowed = active_mask & (TEST_ISOLATION_ENABLED ? hk_mask : 15);
                    reg_value = before;
                    writes = 0;
                    bcm2836_arm_irqchip_spin_gpu_irq();
                    CHECK((reg_value & ~3U) == upper[b], "FIQ/other bits changed");
                    CHECK(writes <= 1, "multiple register writes");
                    if (!active_mask) {
                        CHECK(writes == 0 && reg_value == before, "no-active case changed route");
                    } else {
                        CHECK(writes == 1, "active target was not selected");
                        CHECK(active_mask & (1U << (reg_value & 3)), "offline CPU selected");
                        if (allowed)
                            CHECK(allowed & (1U << (reg_value & 3)), "isolated CPU selected");
                    }
                    cases++;
                }
    /* Repeated IRQs must alternate on CPU0/1 and never escape to CPU2/3. */
    active_mask = 15;
    hk_mask = TEST_ISOLATION_ENABLED ? 3 : 15;
    reg_value = 0;
    u32 seen = 0;
    for (unsigned int i = 0; i < 128; i++) {
        u32 previous = reg_value & 3;
        bcm2836_arm_irqchip_spin_gpu_irq();
        CHECK((reg_value & 3) != previous, "rotation stalled with multiple targets");
        CHECK(hk_mask & (1U << (reg_value & 3)), "rotation escaped allowed CPUs");
        seen |= 1U << (reg_value & 3);
    }
    CHECK(seen == hk_mask, "eligible CPU starved");
    printf("PASS: %u mask/register cases + 128 rotations (CPU_ISOLATION=%d)\n",
           cases, TEST_ISOLATION_ENABLED);
    return 0;
}
"""


def function(source):
    start = source.index("void bcm2836_arm_irqchip_spin_gpu_irq(void)")
    end = source.index("\nEXPORT_SYMBOL(bcm2836_arm_irqchip_spin_gpu_irq);", start)
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_tree", type=Path)
    args = parser.parse_args()
    original = (args.source_tree / DRIVER).read_text()
    with tempfile.TemporaryDirectory(prefix="ahal-irq-test-") as temporary:
        work = Path(temporary)
        driver = work / DRIVER
        driver.parent.mkdir(parents=True)
        driver.write_text(original)
        subprocess.run(
            ["patch", "--batch", "--fuzz=0", "-p1", "-i", str(PATCH.resolve())],
            cwd=work, check=True,
        )
        patched = driver.read_text()
        assert "#include <linux/sched/isolation.h>" in patched
        for enabled in (0, 1):
            source = work / "test.c"
            binary = work / "test"
            source.write_text(PRELUDE + function(patched) + TESTS)
            subprocess.run(
                [os.environ.get("CC", "cc"), "-std=c11", "-O2", "-Wall", "-Wextra",
                 "-Werror", f"-DTEST_ISOLATION_ENABLED={enabled}", str(source),
                 "-o", str(binary)], check=True,
            )
            subprocess.run([str(binary)], check=True)
        # Demonstrate that this harness actually catches the old routing bug.
        source.write_text(PRELUDE + function(original) + TESTS)
        subprocess.run(
            [os.environ.get("CC", "cc"), "-std=c11", "-O2",
             "-DTEST_ISOLATION_ENABLED=1", str(source), "-o", str(binary)], check=True,
        )
        result = subprocess.run([str(binary)], capture_output=True, text=True)
        if result.returncode == 0:
            raise RuntimeError("Regression control unexpectedly accepted the original driver")
        print("PASS: original driver rejected:", result.stderr.strip())
        subprocess.run(
            ["patch", "--batch", "--fuzz=0", "-R", "-p1", "-i", str(PATCH.resolve())],
            cwd=work, check=True,
        )
        assert driver.read_text() == original, "Reverse patch did not restore exact source"
        print("PASS: reverse patch restores exact source")


if __name__ == "__main__":
    main()
