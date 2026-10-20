#!/usr/bin/env python3
"""
iOS 12 compatibility patch for zip_flutter 0.0.12.

The plugin's src/miniz.h implements its file-stat helper on top of
std::filesystem, whose libc++ symbols are only available on iOS 13+.
On Apple platforms we replace that helper with an equivalent POSIX
(lstat/sys/stat.h) implementation. The function signature and the
_stat_struct fields are unchanged, so every other caller is untouched.

Run on the CI after `flutter pub get` with the pub-cache path as argv[1].
"""
import os
import re
import sys

INC_OLD = "#include <filesystem>\n"
INC_NEW = (
    "#if defined(__APPLE__)\n"
    "#include <sys/stat.h>\n"
    "#else\n"
    "#include <filesystem>\n"
    "#endif\n"
)

APPLE_IMPL = """#if defined(__APPLE__)
int _stat(const char* file, _stat_struct* stat) {
    if (!file || !stat) {
        return -1;
    }
    struct stat st;
    if (lstat(file, &st) != 0) {
        return -1;
    }
    std::memset(stat, 0, sizeof(_stat_struct));
    if (S_ISREG(st.st_mode)) {
        stat->st_mode = 0x8000;
    } else if (S_ISDIR(st.st_mode)) {
        stat->st_mode = 0x4000;
    } else if (S_ISLNK(st.st_mode)) {
        stat->st_mode = 0xA000;
    } else {
        stat->st_mode = 0;
    }
    if (st.st_mode & S_IRUSR) stat->st_mode |= 0x100;
    if (st.st_mode & S_IWUSR) stat->st_mode |= 0x80;
    if (st.st_mode & S_IXUSR) stat->st_mode |= 0x40;
    stat->st_size = static_cast<size_t>(st.st_size);
    stat->time = st.st_mtime;
    return 0;
}
#else
__ORIGINAL_STAT__
#endif
"""


def find_miniz_h(pub_cache: str) -> str:
    for root, _dirs, files in os.walk(pub_cache):
        if root.endswith(os.path.join("zip_flutter-0.0.12", "src")) and "miniz.h" in files:
            return os.path.join(root, "miniz.h")
    raise SystemExit("zip_flutter-0.0.12/src/miniz.h not found under " + pub_cache)


def main():
    pub_cache = sys.argv[1]
    path = find_miniz_h(pub_cache)
    print("Patching:", path)
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    if "POSIX_STAT_IOS12_PATCHED" in src:
        print("Already patched, nothing to do.")
        return

    if INC_OLD not in src:
        raise SystemExit("expected #include <filesystem> not found")

    # Only the first occurrence is the unconditional include; the original
    # line is unique in the pristine file, so replacing it once is safe.
    src = src.replace(INC_OLD, INC_NEW + "// POSIX_STAT_IOS12_PATCHED\n", 1)

    # Extract the original _stat(...) function block (from its signature
    # line to the first closing brace at column 0 that follows).
    m = re.search(r"int _stat\(const char\* file, _stat_struct\* stat\) \{", src)
    if not m:
        raise SystemExit("could not locate _stat() function")
    start = m.start()
    end = src.index("\n}\n", start) + len("\n}\n")
    original = src[start:end]

    replacement = APPLE_IMPL.replace("__ORIGINAL_STAT__", original)
    src = src[:start] + replacement + src[end:]

    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("Patch applied.")


if __name__ == "__main__":
    main()
