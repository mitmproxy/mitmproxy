#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/types.h>
#include <sys/capability.h>
#include <unistd.h>
#include <errno.h>

int set_caps(cap_t cap_struct, cap_value_t *caps, int len) {
	if (cap_set_flag(cap_struct, CAP_PERMITTED, len, caps, CAP_SET) ||
            cap_set_flag(cap_struct, CAP_EFFECTIVE, len, caps, CAP_SET) ||
            cap_set_flag(cap_struct, CAP_INHERITABLE, len, caps, CAP_SET)) {
		if (len < 2) {
			fprintf(stderr, "Cannot manipulate capability data structure as user: %s.\n", strerror(errno));
		} else {
			fprintf(stderr, "Cannot manipulate capability data structure as root: %s.\n", strerror(errno));
		}

		return 7;
	}

	if (len < 2) {
		if (prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_RAISE, CAP_NET_RAW, 0, 0)) {
			fprintf(stderr, "Failed to add CAP_NET_RAW to the ambient set: %s.\n", strerror(errno));
			return 88;
		}
	}

	if (cap_set_proc(cap_struct)) {
		if (len < 2) {
			fprintf(stderr, "Cannot set capabilities as user: %s.\n", strerror(errno)); 
		} else {
			fprintf(stderr, "Cannot set capabilities as root: %s.\n", strerror(errno));
		}
		return 1;
	}

	if (len > 1) {
		if (prctl(PR_SET_KEEPCAPS, 1L)) {
			fprintf(stderr, "Cannot keep capabilities after dropping privileges: %s.\n", strerror(errno));
			return 4;
		}
		if (cap_clear(cap_struct)) {
			fprintf(stderr, "Cannot clear capability data structure: %s.\n", strerror(errno));
			return 6;
		}
	}
}

int main(int argc, char **argv, char **envp) {
	cap_t cap_struct = cap_init();
	cap_value_t root_caps[2] = { CAP_NET_RAW, CAP_SETUID };
	cap_value_t user_caps[1] = { CAP_NET_RAW };
	uid_t user = getuid();

	if (setresuid(0, 0, 0)) {
		fprintf(stderr, "Cannot switch to root: %s.\n", strerror(errno));
		return 1;
	}

	set_caps(cap_struct, root_caps, 2);
	if (setresuid(user, user, user)) {
		fprintf(stderr, "Cannot drop root privileges: %s.\n", strerror(errno));
		return 5;
	}
	set_caps(cap_struct, user_caps, 1);

	if (execve(argv[1], argv + 1, envp))
		perror("Cannot exec");
}
