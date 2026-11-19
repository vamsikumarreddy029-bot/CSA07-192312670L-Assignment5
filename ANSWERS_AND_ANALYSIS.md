# Assignment 5 – CO5 | Design answers and engineering analysis

> These are the design calculations and protocol analyses. Measured, simulated and illustrative values are separately identified in `evidence/outputs/execution_manifest.json` and `README.md`.

## A1 – Where does the delay come from?

### A1.1 Delay breakdown
Assume fibre propagation speed = 2 × 10^8 m/s and store-and-forward transmission over four 100 Mbps links (three routers create four links).

- Packet size = 1,500 × 8 = 12,000 bits.
- Transmission per link = 12,000 / 100,000,000 = 0.00012 s = **0.12 ms**; four links = **0.48 ms**.
- Propagation = 2,000,000 / (2 × 10^8) = **0.010 s = 10 ms**.
- Queuing = 3 × 0.5 = **1.5 ms**.
- Processing = 3 × 0.1 = **0.3 ms**.
- Total one-way delay = 0.48 + 10 + 1.5 + 0.3 = **12.28 ms**.

Propagation dominates. Moving all links from 100 Mbps to 1 Gbps reduces transmission from 0.48 ms to 0.048 ms, improving total delay by only 0.432 ms (about 3.5%). It may improve capacity/congestion, but does little to propagation delay.

### A1.2 Bandwidth–delay product
BDP = 1 Gbps × 0.080 s = **80,000,000 bits = 10,000,000 bytes (10 MB decimal)**. A 64 KiB (65,536-byte) TCP window permits at most 65,536 × 8 / 0.080 = **6.5536 Mbps**. The window is far smaller than the BDP, so the sender cannot keep enough data in flight to fill the 1 Gbps path. Window scaling / larger receive window is needed.

### A1.3 Targets and measurement plan
| Application | Suggested target | Active tools | Passive tools |
|---|---|---|---|
| Live video | one-way delay <150 ms; jitter <30 ms; loss <1%; ≥2 Mbps per HD stream | ping/traceroute for path RTT; iperf3; controlled call | Wireshark RTP analysis; SNMP interface counters |
| Voice | one-way delay <150 ms; jitter <30 ms; loss <1%; ≥100 kbps per call including overhead | ping, iperf3 UDP | RTP stream analysis, SNMP |
| Recorded video | sustained throughput ≥1.5× playback bitrate; startup <3 s; loss near 0 after TCP recovery | iperf3, HTTP download timing | Wireshark, SNMP |
| E-mail | transaction response <2 s; loss <1%; modest bandwidth | SMTP/IMAP test, ping | Wireshark protocol timings, SNMP |
| Downloads | throughput ≥70% of provisioned access rate; completion time measured | iperf3 / timed HTTP download | SNMP utilisation, Wireshark |

Active measurement injects probes or test flows and can reveal current end-to-end behaviour, but consumes bandwidth and may not represent application traffic. Passive measurement observes real traffic/counters with low extra load; it can derive observed throughput, packet sizes, retransmissions, protocol timings and interface utilisation. It cannot directly measure an unused path's current delay or loss, and one-way delay needs synchronised clocks. Passive-only monitoring often detects a problem after users start experiencing it; active probes can detect path degradation earlier.

## A2 – Follow the application protocols

### A2.1 SMTP and mailbox access
Example SMTP dialogue (typical replies):
```
S: 220 mail.example.com ESMTP ready
C: EHLO client.example.com
S: 250-mail.example.com
S: 250 SIZE 35882577
C: MAIL FROM:<student@example.com>
S: 250 2.1.0 Sender OK
C: RCPT TO:<teacher@example.edu>
S: 250 2.1.5 Recipient OK
C: DATA
S: 354 End data with <CRLF>.<CRLF>
C: Subject: Assignment
C: Hello, please find the assignment attached.
C: .
S: 250 2.0.0 Message accepted
C: QUIT
S: 221 2.0.0 Bye
```

POP3 configured to delete after download removes the server copy after the first device retrieves it; other devices then see missing mail and folders/read state are not synchronised. IMAP keeps messages on the server and synchronises folders, flags and read state across phone, laptop and lab PC.

### A2.2 FTP, SFTP and SNMP
In active FTP, the client opens the control connection to TCP/21 and tells the server where to connect back for the data channel. A NAT/stateful firewall commonly blocks this unsolicited inbound data connection. In passive FTP, the server advertises a high data port and the client initiates both connections outbound, which traverses typical client firewalls more easily. FTP is unencrypted; SFTP runs over SSH (normally TCP/22), while HTTPS protects file transfer with TLS.

SNMP manager sends GET for an interface counter OID such as `IF-MIB::ifInOctets.2` (or the 64-bit `ifHCInOctets.2`); the agent returns the current counter value. On link failure, the agent sends an asynchronous TRAP such as `IF-MIB::linkDown` to the configured manager. SNMPv3 authPriv is preferred over community-string SNMPv1/v2c.

### A2.3 DNS and HTTP timings
In browser developer tools, inspect DNS Lookup, Initial Connection, SSL/TLS, Request Sent, Waiting/TTFB and Content Download. High DNS time suggests resolver/name lookup delay; high connection/TLS time suggests handshake/path setup; high TTFB suggests server/application processing or upstream delay; high content download suggests large assets or low throughput. Also inspect redirects, blocked requests and waterfall dependencies.

### Alternative: webmail vs IMAP for 50 messages
Assume 50 message headers at roughly 1 KB each (about 50 KB), average body 10 KB (500 KB total), and a webmail UI plus scripts/styles of roughly 0.5–2 MB. Opening only the mailbox list with IMAP can transfer roughly 50–100 KB of headers/metadata, fetching bodies as selected; a browser webmail initial load can transfer around 0.55–2.5 MB including interface assets and messages, depending on caching and previews. These are illustrative estimates, not measured captures. HTTPS webmail centralises browser access control and TLS configuration; IMAP over TLS can be equally encrypted, but requires correct client/server settings on every device.

## A3 – P2P, VoIP and overlays

### A3.1 4 GB distribution
Use 4 GB = 32 Gbits and 20 centres.
- Client–server unicast: server must upload 20 copies = 20 × 32 = 640 Gbits. At 100 Mbps, time = 640,000 Mbit / 100 Mbit/s = **6,400 s = 106.7 min**.
- P2P lower bound using the standard distribution bound: `max(F/us, F/dmin, N×F/(us+sum ui))`. Terms: 32 Gbit/100 Mbps = 320 s; 32 Gbit/50 Mbps = 640 s; 640 Gbit/(100+20×20 Mbps) = 1,280 s. Thus **1,280 s = 21.3 min**. P2P wins because the centres upload pieces to one another, increasing aggregate upload capacity. It may lose with few peers, low peer upload, churn, asymmetric/firewalled clients, coordination overhead or strict integrity/availability requirements.

### A3.2 G.711 voice
20 ms packetisation gives 1/0.020 = **50 packets/s**. Speech payload per packet = 64,000 × 0.020 / 8 = **160 bytes**. Add 40 bytes IP/UDP/RTP = 200 bytes. Bandwidth per direction = 200 × 8 × 50 = **80,000 bps = 80 kbps** (excluding link-layer overhead). A 2 Mbps link therefore supports at most 2,000/80 = **25 calls** in one direction, before safety margin and other traffic. SIP establishes, modifies and terminates sessions; RTP carries real-time media packets.

### A3.3 Overlay networks and CDN alternative
A CDN places replicated/cache servers near users and routes requests to a suitable edge, reducing long-haul delay and origin load. A VPN creates a logical encrypted tunnel over the public Internet, protecting staff/centre connectivity. For a 1 Gbps CDN edge in each region, each centre is still limited by its 50 Mbps download, so 4 GB takes 32 Gbit/50 Mbps = **640 s = 10.7 min** per centre; all centres can download in parallel. CDN is likely faster and more predictable, but incurs provider/storage/egress cost and cache-invalidation/synchronisation work. P2P avoids some origin egress but depends on peer availability and upload capacity.

## A4 – TLS and firewall

TLS certificates bind a public key to a domain identity through a trusted certificate authority and allow the client to authenticate the server (and optionally the client). The handshake negotiates protocol version, cipher suite and key material, then derives symmetric session keys. On café Wi-Fi, a passive attacker can generally see IP addresses, ports, packet sizes/timing and some connection metadata, but not HTTPS application content or credentials when certificate validation and TLS are sound. A malicious proxy/captive portal or compromised endpoint is a different threat.

The given firewall rules are first-match. Rule 2 (`allow tcp any -> 22`) matches every TCP/22 packet, so rule 3 (`deny tcp any -> 22`) and rule 4 (`allow tcp 10.1.0.0/16 -> 22`) can never be reached. This leaves SSH open to all sources. Correct order: allow TCP/22 from 10.1.0.0/16; deny TCP/22 from all other sources; allow TCP/443; allow UDP/53 only if the server actually provides DNS; deny all remaining traffic. Apply least privilege and restrict DNS direction/role.

A stateless filter evaluates each packet independently. A stateful firewall tracks connection state and permits valid return traffic. An application proxy terminates/inspects application sessions (e.g. HTTP methods, URLs, headers) and can enforce higher-layer policy at additional processing cost. The provided Python code uses first-match logic and demonstrates why the order of the allow/deny SSH rules matters.

A cloud WAF can block application-layer attacks such as SQL injection and cross-site scripting, malformed HTTP requests, bot abuse and some HTTP floods; a basic L3/L4 packet filter cannot inspect HTTP semantics. Added latency depends on provider/region and routing; a practical planning estimate might be 5–30 ms per request, to be verified by a pilot. Given the three-hour outage, WAF plus DDoS scrubbing/CDN is justified for a public learning portal.

## A5 – DoS protection

### A5.1 SYN queue
If 1,024 half-open entries remain for 60 s, queue fill rate = 1,024/60 = **17.07 SYN/s** (assuming no legitimate completions/eviction). SYN cookies encode state into the SYN-ACK sequence number so the server need not allocate a full connection entry until the final ACK returns; they reduce half-open queue exhaustion but do not add bandwidth or protect all application-layer floods. DNS amplification is hard to block at the victim because responses are sent to the victim's spoofed source address and can arrive from many legitimate open resolvers; upstream filtering, source-address validation and DDoS scrubbing are needed.

### A5.2 Protection plan and four-server alternative
- SYN flood: enable SYN cookies, per-source/connection rate controls, state-table protection and upstream scrubbing.
- DNS amplification/volumetric flood: upstream DDoS scrubbing, CDN/Anycast distribution, authoritative DNS hardening and provider coordination; rate limiting only at the victim may be too late because the access link is already saturated.
- HTTP request flood: WAF/bot controls, CDN caching, application rate limits and autoscaling.
- Four times the queue capacity gives 4,096 half-open slots; at 60 s timeout, fill rate is 4,096/60 = **68.27 SYN/s**. This only quadruples the threshold and is not a realistic standalone defence against a distributed attacker.

## B1 – Real network measurements and trace analysis

The trace-metrics program reproduces the assignment's supplied sample exactly: 20% loss, 42.9 ms average one-way delay, 6.6 ms jitter and 345.9 kbps. Removing the two lost records makes loss 0%; delay/jitter remain 42.9/6.6 ms and quality passes the supplied simple threshold. This is analysis of the assignment-provided trace, not a live capture.

The package also ran actual TCP and UDP socket transfers on local loopback and an actual traceroute command to 1.1.1.1. Loopback is a local host-stack benchmark, not a wired or Wi-Fi path. The container disallowed raw ICMP ping, and did not contain Wireshark/TShark/iperf3. Therefore no real call capture or wired-versus-wireless result is claimed. The included `.pcap` is a synthetic RTP-like fixture for opening/decoder testing only.

One-way delay requires synchronised clocks at sender and receiver. Half-RTT is not necessarily one-way delay: if upload is 80 ms and download is 20 ms, RTT is 100 ms and half-RTT is 50 ms, while the forward one-way delay is 80 ms (30 ms underestimate).

## B2 – Simulation

`run_all.py` generates a deterministic regional learning network model and sweeps link bandwidth (50/100/200 Mbps), base delay (20/80/150 ms), user load, background download and voice priority. It exports a CSV and plots. These are model results, not Packet Tracer or NS-3 outputs. The model is intentionally reproducible and transparent; its simplified traffic assumptions should be replaced by calibrated measurements in the final deployment study. Priority queueing protects voice delay by serving the voice class first, but can reduce best-effort download throughput and must be policed to prevent starvation.

## B3 – Stress, window and security

`B3_impairment_matrix.csv` covers all nine requested combinations (50/150/300 ms added delay × 1/5/10% configured loss). It is a deterministic impairment model, not kernel `tc netem`. The BDP calculation in A1.2 shows why a 64 KiB window caps throughput at about 6.55 Mbps on an 80 ms RTT 1 Gbps path; a window near 10 MB is needed to fill the path (ignoring congestion-control and receiver limitations). SYN queue and rate-limit arithmetic is in `A5_B3_SYN_and_rate_limit.json`. No live flood was sent; DoS testing must remain in an isolated lab. Strict-priority EF gives the lowest voice delay but can starve downloads; weighted fair queuing is safer when voice and data both need guaranteed shares. Use EF for tightly controlled voice traffic with policing, or WFQ when fairness is a stronger requirement.

## B4 – Final engineering decision

The included doubled-user prediction is model-derived. The real intercontinental RTT and doubled-load measurements were not available in this restricted environment, so the result is not represented as measured. Engineering recommendation: deploy regional CDN/cache and live-media relays, add geographically distributed session infrastructure, use QoS (EF for voice with policing and fair queuing for data), enable WAF/DDoS scrubbing/SYN cookies, increase origin and uplink capacity based on measured peak utilisation, and continuously monitor per-application delay/jitter/loss/throughput. Regional servers reduce propagation delay approximately by replacing the India-to-user path with the nearer regional path; quantify the saving using measured RTTs before committing to synchronisation and hosting costs.
