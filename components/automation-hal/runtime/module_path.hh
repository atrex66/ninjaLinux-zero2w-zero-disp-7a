// SPDX-License-Identifier: GPL-2.0-or-later
// Standalone HAL extension: explicit app directories, immutable system priority.
#pragma once
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <string>
#include <sys/stat.h>

inline bool ahal_module_path(const std::string &name, const std::string &system,
                             const char *extra, std::string &path, std::string &error) {
    if (name.empty() || name.find('/') != std::string::npos || name.find("..") != std::string::npos) {
        error = "Invalid module name";
        return false;
    }
    path = system + "/" + name + ".so";
    struct stat info;
    if (lstat(path.c_str(), &info) == 0)
        return true; // Never substitute an app version for an existing system file.
    if (errno != ENOENT) {
        error = "Cannot inspect system module: " + std::string(strerror(errno));
        return false;
    }
    if (name == "hal_lib") {
        error = "Core hal_lib must be provided by the system";
        return false;
    }
    std::string directories = extra ? extra : "";
    size_t start = 0;
    while (start < directories.size()) {
        size_t end = directories.find(':', start);
        std::string directory = directories.substr(start, end == std::string::npos ? end : end-start);
        if (directory.empty() || directory[0] != '/') {
            error = "Module directories must be absolute";
            return false;
        }
        std::string candidate = directory + "/" + name + ".so";
        if (lstat(candidate.c_str(), &info) == 0) {
            if (!S_ISREG(info.st_mode)) {
                error = "App module must be a regular file, not a symlink or device";
                return false;
            }
            path = candidate;
            return true;
        }
        if (errno != ENOENT) {
            error = "Cannot inspect app module: " + std::string(strerror(errno));
            return false;
        }
        if (end == std::string::npos) break;
        start = end + 1;
    }
    error = "Module not found in system or configured app directories";
    return false;
}
