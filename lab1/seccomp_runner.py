import errno
import os
import sys

import seccomp


allowed_syscalls = [
    "accept4",
    "access",
    "arch_prctl",
    "bind",
    "brk",
    "clock_gettime",
    "clone3",
    "close",
    "epoll_create1",
    "epoll_ctl",
    "epoll_pwait",
    "eventfd2",
    "execve",
    "exit",
    "exit_group",
    "fcntl",
    "fstat",
    "futex",
    "getcwd",
    "getdents64",
    "getpeername",
    "getpid",
    "getrandom",
    "getsockname",
    "gettid",
    "ioctl",
    "io_uring_enter",
    "io_uring_setup",
    "listen",
    "lseek",
    "madvise",
    "mmap",
    "mprotect",
    "munmap",
    "newfstatat",
    "openat",
    "pipe2",
    "pread64",
    "prlimit64",
    "read",
    "readlink",
    "recvfrom",
    "rseq",
    "rt_sigaction",
    "rt_sigprocmask",
    "rt_sigreturn",
    "set_robust_list",
    "setsockopt",
    "set_tid_address",
    "socket",
    "socketpair",
    "tgkill",
    "uname",
    "write",
    "writev",
]


# все запрещаем по умолчанию
filt = seccomp.SyscallFilter(
    defaction=seccomp.ERRNO(errno.EPERM)
)

# разрешаем то что процесс использовал в стрейсе
for syscall in allowed_syscalls:
    filt.add_rule(seccomp.ALLOW, syscall)

# Загружаем фильтр в ядро
filt.load()


# проверка фильтра
'''
try:
    os.mkdir("/tmp/seccomp-test")
    print("err: mkdir не был заблокирован")
    raise SystemExit(1)
except PermissionError:
    print("done: mkdir заблокирован seccomp")
'''

os.execvp(sys.argv[1], sys.argv[1:])