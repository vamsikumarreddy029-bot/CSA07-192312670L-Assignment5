# CSA07 – Assignment 5 (CO5): Measuring Network Performance and Securing Applications

**Student name:** [Fill in]  
**Register number:** [Fill in]  
**Operating system used for the recorded execution:** Linux x86_64 container (kernel 6.18.57)  
**Python:** 3.13.5  
**Cisco Packet Tracer / NS-3:** Not installed in the execution environment; no version claimed  
**Wireshark / TShark / iperf3:** Not installed in the execution environment; no version claimed  

## Repository contents

- `Task01`–`Task05`: Part A design and protocol/security analyses.
- `Task06`–`Task09`: Part B measurement, simulation, stress model and engineering decision.
- `run_all.py`: reproducible runner. Completes both assignment-provided Python TODO programs, performs actual local TCP/UDP socket tests, executes traceroute, generates simulation matrices, graphs and a synthetic PCAP fixture.
- `ANSWERS_AND_ANALYSIS.md`: worked calculations, protocol sequences, firewall analysis and engineering interpretation.
- `evidence/outputs`: machine-readable JSON/CSV and captured command outputs.
- `evidence/graphs`: charts generated from actual loopback measurements or explicitly labelled simulation data.
- `evidence/topologies`: Python-rendered simulation topology (not a Packet Tracer screenshot).
- `evidence/packet_traces`: synthetic RTP-like PCAP fixture for parser practice (not captured from a real call).
- `configs`: firewall policy examples.

## Run

Requires Python 3.10+ plus `matplotlib` and `numpy` for plots. The runner uses the Python standard library for socket tests and calculations.

```bash
python3 -m pip install matplotlib numpy
python3 run_all.py
```

The runner recreates the output files under `evidence/`. It performs a TCP and UDP transfer over localhost and runs `traceroute -m 5 -w 1 1.1.1.1` if the command exists. ICMP ping was blocked by raw-socket permissions in the execution environment.

## Evidence provenance and important limitations

This package intentionally separates **actual measurements**, **assignment-provided sample-trace analysis**, and **modelled results**:

1. `B1_local_socket_measurements.json` contains actual TCP/UDP loopback socket test results. Loopback is not a physical LAN, campus wired link or Wi-Fi measurement.
2. `B1_traceroute_actual.txt` contains the actual traceroute command output from the execution host. The route is environment/container-specific.
3. `B1_trace_metrics.txt` is computed from the packet trace supplied in the assignment question, not from a live Wireshark capture.
4. `B2_simulation_matrix.csv`, `B3_impairment_matrix.csv` and `B4_scaling_prediction.json` are reproducible Python model outputs, not Cisco Packet Tracer/NS-3 or `tc netem` results.
5. `B1_synthetic_rtp_like_trace.pcap` is a generated PCAP fixture for testing packet-trace inspection. It is not a captured voice/video call and must not be submitted as live Wireshark evidence.

Cisco Packet Tracer, Wireshark GUI, TShark, iperf3 and NS-3 were not installed in the execution environment. Therefore no `.pkt` file, genuine Packet Tracer screenshot, live Wireshark capture/screenshot, `iperf3` result, kernel `tc netem` result, wired-versus-wireless comparison or intercontinental path measurement is claimed. These require execution on a machine with the respective tools. Do not relabel the supplied simulation/fixture outputs as those tools' evidence.

## Task summary

| Task | Deliverable | Status |
|---|---|---|
| A1 | Delay and BDP calculations; metric targets | Completed |
| A2 | SMTP/POP3/IMAP, FTP/SFTP, SNMP, DNS/HTTP analysis | Completed |
| A3 | Client-server/P2P/CDN distribution and VoIP calculations | Completed |
| A4 | TLS/firewall analysis and completed Python TODO | Completed and executed |
| A5 | SYN queue calculation and protection plan | Completed |
| B1 | Trace-metrics TODO, local socket tests, traceroute | Partially measured; limitations documented |
| B2 | Parameter-sweep Python simulation | Executed; not Packet Tracer/NS-3 |
| B3 | Delay/loss matrix and SYN/rate-limit arithmetic | Model executed; not `tc netem` or live attack |
| B4 | Doubled-load prediction and recommendations | Model-derived; WAN measurements unavailable |

## Before submission

- Fill in student name and register number.
- Add the actual GitHub repository URL to the report cover page and submission form.
- The assignment specifically requires a working repository and progressive commits. Use `create_task_commits.sh` to create one commit for each task folder after reviewing the contents; then push to your GitHub repository.
- Complete the missing Packet Tracer/NS-3 and Wireshark/iperf3 tasks on a machine where those tools are installed if the faculty expects native simulator/capture evidence. This ZIP does not pretend those unavailable experiments were performed.
