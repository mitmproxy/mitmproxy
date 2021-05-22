#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/types.h>
#include <sys/capability.h>
#include <unistd.h>
#include <errno.h>

/* This setuid wrapper can be used to run mitmproxy in full transparency mode, as a normal user.
 * It will set the required capabilities (CAP_NET_RAW), drop privileges, and will then run argv[1]
 * with the same capabilities.
 *
 * It can be compiled as follows:
 * gcc examples/mitmproxy_shim.c -o mitmproxy_shim -lcap
*/

int set_caps(cap_t cap_struct, cap_value_t *cap_list, size_t bufsize) {
	int cap_count = bufsize / sizeof(cap_list[0]);

	if (cap_set_flag(cap_struct, CAP_PERMITTED, cap_count, cap_list, CAP_SET) ||
            cap_set_flag(cap_struct, CAP_EFFECTIVE, cap_count, cap_list, CAP_SET) ||
            cap_set_flag(cap_struct, CAP_INHERITABLE, cap_count, cap_list, CAP_SET)) {
		if (cap_count < 2) {
			fprintf(stderr, "Cannot manipulate capability data structure as user: %s.\n", strerror(errno));
		} else {
			fprintf(stderr, "Cannot manipulate capability data structure as root: %s.\n", strerror(errno));
		}
		return -1;
	}

	if (cap_count < 2) {
		if (prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_RAISE, CAP_NET_RAW, 0, 0)) {
			fprintf(stderr, "Failed to add CAP_NET_RAW to the ambient set: %s.\n", strerror(errno));
			return -2;
		}
	}

	if (cap_set_proc(cap_struct)) {
		if (cap_count < 2) {
			fprintf(stderr, "Cannot set capabilities as user: %s.\n", strerror(errno)); 
		} else {
			fprintf(stderr, "Cannot set capabilities as root: %s.\n", strerror(errno));
		}
		return -3;
	}

	if (cap_count > 1) {
		if (prctl(PR_SET_KEEPCAPS, 1L)) {
			fprintf(stderr, "Cannot keep capabilities after dropping privileges: %s.\n", strerror(errno));
			return -4;
		}
		if (cap_clear(cap_struct)) {
			fprintf(stderr, "Cannot clear capability data structure: %s.\n", strerror(errno));
			return -5;
		}
	}
}

int main(int argc, char **argv, char **envp) {
	cap_t cap_struct = cap_init();
	cap_value_t root_caps[2] = { CAP_NET_RAW, CAP_SETUID };
	cap_value_t user_caps[1] = { CAP_NET_RAW };
	uid_t user = getuid();
	int res;

	if (setresuid(0, 0, 0)) {
		fprintf(stderr, "Cannot switch to root: %s.\n", strerror(errno));
		return 1;
	}

	if (res = set_caps(cap_struct, root_caps, sizeof(root_caps)))
		return res;

	if (setresuid(user, user, user)) {
		fprintf(stderr, "Cannot drop root privileges: %s.\n", strerror(errno));
		return 2;
	}

	if (res = set_caps(cap_struct, user_caps, sizeof(user_caps)))
		return res;

	if (execve(argv[1], argv + 1, envp)) {
		fprintf(stderr, "Failed to execute %s: %s\n", argv[1], strerror(errno));
		return 3;
	}
}
