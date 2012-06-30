import socket, struct

# Python socket module does not have this constant
DIOCNATLOOK = 23

class Resolver:
    def original_addr(self, csock):
        """
            The following sttruct defintions are plucked from the current XNU source, found here:

                http://www.opensource.apple.com/source/xnu/xnu-1699.26.8/bsd/net/pfvar.h


            union pf_state_xport {
                u_int16_t	port;
                u_int16_t	call_id;
                u_int32_t	spi;
            };

            struct pf_addr {
                union {
                    struct in_addr		v4;
                    struct in6_addr		v6;
                    u_int8_t		addr8[16];
                    u_int16_t		addr16[8];
                    u_int32_t		addr32[4];
                } pfa;

            struct pfioc_natlook {
                struct pf_addr	 saddr;
                struct pf_addr	 daddr;
                struct pf_addr	 rsaddr;
                struct pf_addr	 rdaddr;
            #ifndef NO_APPLE_EXTENSIONS
                union pf_state_xport	sxport;
                union pf_state_xport	dxport;
                union pf_state_xport	rsxport;
                union pf_state_xport	rdxport;
                sa_family_t	 af;
                u_int8_t	 proto;
                u_int8_t	 proto_variant;
                u_int8_t	 direction;
            #else
                u_int16_t	 sport;
                u_int16_t	 dport;
                u_int16_t	 rsport;
                u_int16_t	 rdport;
                sa_family_t	 af;
                u_int8_t	 proto;
                u_int8_t	 direction;
            #endif
            };
        """
        pass
