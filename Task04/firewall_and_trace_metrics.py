#!/usr/bin/env python3
"""Reproducible CO5 lab: measured loopback sockets + deterministic network simulation.
No Packet Tracer/NS-3/Wireshark/iperf3 dependency. Simulation outputs are explicitly labelled.
"""
from __future__ import annotations
import csv, json, math, os, socket, struct, subprocess, sys, time, random, statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
EV=ROOT/'evidence'; OUT=EV/'outputs'; GR=EV/'graphs'; PC=EV/'packet_traces'
for p in (OUT,GR,PC): p.mkdir(parents=True,exist_ok=True)

# A4: complete the supplied first-match firewall function.
RULES=[('allow','tcp',443,None),('allow','tcp',22,'10.1.'),('deny','tcp',22,None),('allow','udp',53,None)]
def decide(proto,port,src,rules=RULES):
    for action,p,dport,prefix in rules:
        if p==proto and (dport is None or dport==port) and (prefix is None or src.startswith(prefix)):
            return action
    return 'deny'
packets=[('tcp',443,'49.37.2.8'),('tcp',22,'10.1.4.20'),('tcp',22,'49.37.2.8'),('udp',53,'10.1.4.20'),('tcp',80,'49.37.2.8'),('icmp',None,'49.37.2.8')]
fw_lines=[]
for pk in packets: fw_lines.append(f'{pk[0]:<5} {str(pk[1]):<5} from {pk[2]:<10} -> {decide(*pk)}')
swapped=RULES.copy(); swapped[1],swapped[2]=swapped[2],swapped[1]
fw_lines += ['', 'After swapping rules 2 and 3:']
for pk in packets: fw_lines.append(f'{pk[0]:<5} {str(pk[1]):<5} from {pk[2]:<10} -> {decide(*pk, rules=swapped)}')
(OUT/'A4_firewall_output.txt').write_text('\n'.join(fw_lines)+'\n')

# B1: complete supplied trace metrics function.
TRACE=[(1,0,42,1200),(2,20,61,1200),(3,40,85,1200),(4,60,None,1200),(5,80,119,1200),(6,100,146,1200),(7,120,158,1200),(8,140,190,1200),(9,160,None,1200),(10,180,222,1200)]
def metrics(trace):
    got=[(s,tx,rx,b) for s,tx,rx,b in trace if rx is not None]
    loss=100*(len(trace)-len(got))/len(trace)
    delays=[rx-tx for _,tx,rx,_ in got]
    avg_delay=statistics.mean(delays)
    jitter=statistics.mean(abs(b-a) for a,b in zip(delays,delays[1:])) if len(delays)>1 else 0.0
    elapsed=got[-1][2]-got[0][1]
    throughput=sum(b for _,_,_,b in got)*8/elapsed # kbps because bits/ms == kbps
    return loss,avg_delay,jitter,throughput
m=metrics(TRACE)
no_loss=[(s,tx,rx,b) for s,tx,rx,b in TRACE if rx is not None]
m2=metrics(no_loss)
(OUT/'B1_trace_metrics.txt').write_text(f'packet loss {m[0]:.1f} %\naverage delay {m[1]:.1f} ms, jitter {m[2]:.1f} ms\nthroughput {m[3]:.1f} kbps\nVoIP quality: {"acceptable" if m[1]<150 and m[2]<30 and m[0]<1 else "poor"}\n\nAfter removing the two lost packets:\npacket loss {m2[0]:.1f} %\naverage delay {m2[1]:.1f} ms, jitter {m2[2]:.1f} ms\nthroughput {m2[3]:.1f} kbps\nVoIP quality: {"acceptable" if m2[1]<150 and m2[2]<30 and m2[0]<1 else "poor"}\n')

# Actual localhost TCP and UDP socket tests (real measurements on this execution host).
def tcp_loopback_test(total=12*1024*1024, chunk=65536):
    srv=socket.socket(); srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); srv.bind(('127.0.0.1',0)); srv.listen(1); port=srv.getsockname()[1]
    received=[0]
    def server():
        c,_=srv.accept()
        with c:
            while True:
                b=c.recv(chunk)
                if not b: break
                received[0]+=len(b)
    import threading
    th=threading.Thread(target=server); th.start(); c=socket.socket(); c.connect(('127.0.0.1',port)); payload=b'X'*chunk
    t0=time.perf_counter(); sent=0
    while sent<total:
        b=payload[:min(chunk,total-sent)]; c.sendall(b); sent+=len(b)
    c.shutdown(socket.SHUT_WR); c.close(); th.join(); elapsed=time.perf_counter()-t0; srv.close()
    return {'bytes':received[0],'seconds':elapsed,'throughput_mbps':received[0]*8/elapsed/1e6}
def udp_loopback_test(count=10000, size=1200):
    srv=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); srv.bind(('127.0.0.1',0)); srv.settimeout(2); port=srv.getsockname()[1]
    got=[0]
    def receiver():
        end=time.perf_counter()+4
        while time.perf_counter()<end:
            try: srv.recvfrom(2048); got[0]+=1
            except socket.timeout: break
    import threading
    th=threading.Thread(target=receiver); th.start(); cli=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); payload=b'U'*size
    t0=time.perf_counter()
    for _ in range(count): cli.sendto(payload,('127.0.0.1',port))
    elapsed=time.perf_counter()-t0; th.join(); cli.close(); srv.close()
    return {'sent_packets':count,'received_packets':got[0],'loss_percent':100*(count-got[0])/count,'payload_bytes':size,'send_duration_s':elapsed,'sender_rate_mbps':count*size*8/elapsed/1e6}

tcp=tcp_loopback_test(); udp=udp_loopback_test()
(OUT/'B1_local_socket_measurements.json').write_text(json.dumps({'environment':'local loopback on Linux container; not campus/wired/Wi-Fi','tcp':tcp,'udp':udp},indent=2)+'\n')

# Actual traceroute command, if available. Ping raw sockets are restricted in this container.
tr='traceroute -m 5 -w 1 1.1.1.1'
try:
    r=subprocess.run(tr.split(),capture_output=True,text=True,timeout=15)
    (OUT/'B1_traceroute_actual.txt').write_text('$ '+tr+'\n'+r.stdout+r.stderr+f'\nexit_code={r.returncode}\n')
except Exception as e: (OUT/'B1_traceroute_actual.txt').write_text(f'Could not run traceroute: {e}\n')

# A1 calculations.
packet_bits=1500*8; tx_ms_per_link=packet_bits/100e6*1000
tx_ms=tx_ms_per_link*4 # four store-and-forward links (three routers)
prop_ms=2_000_000/2e8*1000 # assumed fibre propagation speed 2e8 m/s
queue_ms=3*0.5; proc_ms=3*0.1; total_ms=tx_ms+prop_ms+queue_ms+proc_ms
bdp_bits=1e9*0.080; bdp_bytes=bdp_bits/8; win_thr=64*1024*8/0.080/1e6
A1={'transmission_ms_per_link':tx_ms_per_link,'transmission_ms_all_4_links':tx_ms,'propagation_ms_one_way':prop_ms,'queuing_ms':queue_ms,'processing_ms':proc_ms,'total_ms':total_ms,'bdp_bits':bdp_bits,'bdp_bytes':bdp_bytes,'64KiB_window_max_Mbps':win_thr}
(OUT/'A1_calculations.json').write_text(json.dumps(A1,indent=2)+'\n')

# B2 reproducible end-to-end network model: bottleneck, propagation, queue, loss; priority protects voice.
def simulate(bw_mbps=100,delay_ms=30,users=100,background=False,priority=False,seed=42):
    rng=random.Random(seed); offered=users*0.35 # Mbps aggregate video+web
    voice=0.064*40 # 40 simultaneous G.711 calls, each 64 kbps => 2.56 Mbps
    bg=35 if background else 0
    demand=offered+voice+bg
    util=min(demand/bw_mbps,1.0)
    queue=max(0,demand-bw_mbps)
    if priority: voice_delay=delay_ms+2.0+max(0,voice/bw_mbps)*4; data_thr=min(max(0,bw_mbps-voice),offered+bg)
    else: voice_delay=delay_ms+2+queue*0.8+util*12; data_thr=min(bw_mbps,max(0,offered+bg))
    loss=max(0,min(20,(demand-bw_mbps)/max(demand,1)*100 + (2 if delay_ms>=150 else 0)))
    jitter=max(1.0,voice_delay*0.08+rng.uniform(0,1.5))
    return {'bandwidth_Mbps':bw_mbps,'one_way_base_delay_ms':delay_ms,'users':users,'background_download':background,'voice_priority':priority,'offered_load_Mbps':round(demand,3),'utilisation_pct':round(util*100,2),'voice_delay_ms':round(voice_delay,2),'voice_jitter_ms':round(jitter,2),'packet_loss_pct':round(loss,2),'data_throughput_Mbps':round(data_thr,2)}
scenarios=[]
for bw in (50,100,200):
 for d in (20,80,150): scenarios.append(simulate(bw,d,100,True,False))
for priority in (False,True): scenarios.append(simulate(100,80,100,True,priority))
with (OUT/'B2_simulation_matrix.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=scenarios[0].keys()); w.writeheader(); w.writerows(scenarios)

# B3 controlled impairment matrix, emulated in reproducible model, not tc netem.
stress=[]
for delay in (50,150,300):
 for loss in (1,5,10):
  # illustrative voice stream: delay/jitter grows with imposed delay; loss is configured impairment.
  stress.append({'added_delay_ms':delay,'configured_loss_pct':loss,'voice_one_way_delay_ms':round(35+delay,1),'voice_jitter_ms':round(4+delay*0.06,1),'voice_packet_loss_pct':loss,'tcp_goodput_relative_pct':round(100*(1-loss/100)*math.exp(-delay/1200),1)})
with (OUT/'B3_impairment_matrix.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=stress[0].keys()); w.writeheader(); w.writerows(stress)
# SYN queue calculations and safe synthetic rate-limit demonstration.
syn={'half_open_queue':1024,'timeout_s':60,'fill_rate_pps':1024/60,'four_server_queue':4096,'four_server_fill_rate_pps':4096/60,'test_rate_pps':100,'limit_pps':20,'accepted_pps':20,'dropped_or_deferred_pps':80}
(OUT/'A5_B3_SYN_and_rate_limit.json').write_text(json.dumps(syn,indent=2)+'\n')

# B4 scaling predictions from model, transparent assumptions.
b4=[]
for users in (100,200):
 b4.append(simulate(100,80,users,True,True))
(OUT/'B4_scaling_prediction.json').write_text(json.dumps({'basis':'model estimates, not WAN measurement','baseline':b4[0],'doubled_users':b4[1],'regional_server_note':'replace long-haul RTT with measured regional path RTT; actual intercontinental path not measured in this restricted environment'},indent=2)+'\n')

# Charts as evidence images (model/measurements labelled accurately).
plt.figure(figsize=(8,4.5)); labels=['TCP loopback','UDP sender rate']; vals=[tcp['throughput_mbps'],udp['sender_rate_mbps']]
plt.bar(labels,vals); plt.ylabel('Mbps'); plt.title('Actual local socket test (loopback; not LAN/Wi-Fi)'); plt.tight_layout(); plt.savefig(GR/'B1_local_socket_throughput.png',dpi=160); plt.close()
plt.figure(figsize=(8,4.5));
for bw in (50,100,200):
 vals=[next(x['voice_delay_ms'] for x in scenarios if x['bandwidth_Mbps']==bw and x['one_way_base_delay_ms']==d) for d in (20,80,150)]
 plt.plot([20,80,150],vals,marker='o',label=f'{bw} Mbps')
plt.xlabel('Base one-way delay (ms)'); plt.ylabel('Modelled voice delay (ms)'); plt.title('B2 simulation: bandwidth and propagation-delay sweep'); plt.legend(); plt.tight_layout(); plt.savefig(GR/'B2_delay_sweep.png',dpi=160); plt.close()
plt.figure(figsize=(8,4.5));
for loss in (1,5,10):
 vals=[next(x['tcp_goodput_relative_pct'] for x in stress if x['configured_loss_pct']==loss and x['added_delay_ms']==d) for d in (50,150,300)]
 plt.plot([50,150,300],vals,marker='o',label=f'{loss}% loss')
plt.xlabel('Added delay (ms)'); plt.ylabel('Relative TCP goodput (%)'); plt.title('B3 impairment model (relative estimate)'); plt.legend(); plt.tight_layout(); plt.savefig(GR/'B3_stress_matrix.png',dpi=160); plt.close()

# Draw network topology; diagram is our Python simulation, not Packet Tracer.
fig,ax=plt.subplots(figsize=(10,5)); ax.axis('off')
coords={'Internet':(0.1,.5),'Edge FW':(.32,.5),'Core Router':(.53,.5),'Regional Centre':(.78,.78),'Learning Server':(.78,.5),'Student Clients':(.78,.2)}
for name,(x,y) in coords.items():
 ax.text(x,y,name,ha='center',va='center',bbox=dict(boxstyle='round,pad=.6',fc='white',ec='black'),fontsize=10)
for a,b in [('Internet','Edge FW'),('Edge FW','Core Router'),('Core Router','Regional Centre'),('Core Router','Learning Server'),('Core Router','Student Clients')]:
 x1,y1=coords[a]; x2,y2=coords[b]; ax.annotate('',(x2-.07,y2),(x1+.07,y1),arrowprops=dict(arrowstyle='<->',lw=1.5))
ax.set_title('CO5 regional learning network – Python simulation topology (not Packet Tracer)'); fig.tight_layout(); fig.savefig(EV/'topologies'/'B2_python_simulation_topology.png',dpi=160); plt.close(fig)

# Create an RFC-compliant classic PCAP containing a synthetic RTP-like UDP trace for parser/Wireshark opening.
def ip_checksum(data):
 if len(data)%2: data+=b'\0'
 s=sum(struct.unpack('!%dH'%(len(data)//2),data)); s=(s>>16)+(s&0xffff); s+=(s>>16); return (~s)&0xffff
pcap=PC/'B1_synthetic_rtp_like_trace.pcap'
with pcap.open('wb') as f:
 f.write(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,1)) # Ethernet
 for i in range(1,11):
  ts=1_700_000_000+i*0.02; sec=int(ts); usec=int((ts-sec)*1e6)
  payload=bytes([0x80,0x60,(i>>8)&255,i&255])+b'RTP-DEMO'+bytes(140)
  udp_segment=struct.pack('!HHHH',5004,5004,8+len(payload),0)+payload
  src=bytes([192,0,2,10]); dst=bytes([198,51,100,20]); iph=struct.pack('!BBHHHBBH4s4s',0x45,0,20+len(udp_segment),i,0,64,17,0,src,dst); chk=ip_checksum(iph); iph=iph[:10]+struct.pack('!H',chk)+iph[12:]
  eth=bytes.fromhex('0200000000020200000000010800'); frame=eth+iph+udp_segment
  f.write(struct.pack('<IIII',sec,usec,len(frame),len(frame))+frame)
(OUT/'EVIDENCE_PROVENANCE.txt').write_text('B1_synthetic_rtp_like_trace.pcap is a generated RFC-compliant Ethernet/IPv4/UDP PCAP fixture for demonstrating trace inspection. It is NOT captured from a real voice/video call and must not be represented as a Wireshark capture. Open it in Wireshark locally if available.\n')

# Results manifest and task readme.
manifest={'actual_measurements':{'localhost_tcp_udp_sockets':tcp|udp,'traceroute':'command executed; see B1_traceroute_actual.txt','ping':'not executed: raw ICMP sockets blocked by host permissions'},'completed_code':{'A4_firewall':True,'B1_metrics':True},'simulations':{'B2':len(scenarios),'B3':len(stress),'B4':True},'unavailable_tools':['Cisco Packet Tracer','Wireshark GUI','TShark','iperf3','NS-3'],'not_performed':['Packet Tracer .pkt simulation and screenshots','Wireshark live capture and GUI screenshots','tc netem kernel impairment (not available/verified)','wired-versus-wireless LAN measurements','intercontinental path measurements']}
(OUT/'execution_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

print('A4 firewall: completed; output -> evidence/outputs/A4_firewall_output.txt')
print(f'B1 trace metrics: loss={m[0]:.1f}%, delay={m[1]:.1f}ms, jitter={m[2]:.1f}ms, throughput={m[3]:.1f}kbps')
print(f'B1 TCP loopback: {tcp["throughput_mbps"]:.2f} Mbps; UDP sender rate: {udp["sender_rate_mbps"]:.2f} Mbps; UDP received {udp["received_packets"]}/{udp["sent_packets"]}')
print(f'B2 simulation rows: {len(scenarios)}; B3 impairment rows: {len(stress)}')
print(f'A1 total delay: {total_ms:.3f} ms; 64KiB window throughput: {win_thr:.3f} Mbps')
