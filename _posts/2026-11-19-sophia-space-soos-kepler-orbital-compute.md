---
title: "Sophia Space runs its orbital operating system across Kepler satellites"
date: 2026-11-19 05:40:00 +0000
summary: "Sophia Space says its software has spread itself across processors on two Kepler relay satellites, a first step toward distributed computing in orbit."
category: industry
story_key: sophia-space-soos-kepler
image:
  path: https://thumb.wikimedia.org/wikipedia/commons/thumb/2/2a/KIPP_-_Kepler%27s_1st_demo_satellite.jpg/1280px-KIPP_-_Kepler%27s_1st_demo_satellite.jpg
  alt: "KIPP, Kepler Communications' first demonstration satellite (archive image, not part of this test)"
  credit: "Victoriaenlanet / Wikimedia Commons"
  license: "CC BY-SA 4.0"
  source_url: https://commons.wikimedia.org/wiki/File:KIPP_-_Kepler%27s_1st_demo_satellite.jpg
sources:
  - name: Payload
    title: "Sophia Space Tests Orbital-Compute Software on Kepler Constellation"
    url: https://payloadspace.com/sophia-space-tests-orbital-compute-software-on-kepler-constellation/
---

Sophia Space has deployed its Sophia Orbital Operating System, or SOOS, across several of Kepler Communications' optical data-relay satellites, Payload reported on Thursday. The company calls it the first in-space milestone on the way to scalable orbital computing.

The test was deliberately simple. An alpha version of the software was uploaded to a single processor on one Kepler satellite. It checked itself, copied itself onto two more processors to form a local network, then reached across an optical link to a second satellite and repeated the process. Success meant the two spacecraft could talk to each other. Sophia CEO and cofounder Rob DeMillo said it would be "the first time there will be a distributed network computer in orbit."

## What SOOS is meant to do

SOOS uses managed Kubernetes, a common cloud tool for scheduling jobs across many machines, so that work can be spread over multiple satellites instead of being stuck on one. It runs on three processors per satellite with a fourth held in reserve, and includes built-in security.

Kepler is a convenient host. The company announced its compute hardware in March, and its Tranche 1 satellites each carry four NVIDIA Jetson Orin processors, the same chip type and count Sophia plans to use in its first TILE compute modules.

Sophia is pitching the software for orbital AI inference: missile warning, Space Development Agency work, maritime awareness, disaster response, weather intelligence and in-space manufacturing. It has signed a contract extension with Kepler and has one paying customer, with a second ready to start. Neither is named. Sophia says it charges for GPU time much as a data center would.

## The hard part is still ahead

Running software on someone else's processors is the easy half. Sophia's own passively cooled hardware has yet to fly, and the company plans to launch its first TILEs in 2028. Its stated main challenge is scaling manufacturing to thousands of servers per month.

The result is a small, early-stage demonstration, reported from a single outlet and based on the company's own account. Still, it shows how orbital compute is starting to look like a layered industry: relay operators supplying chips and links, and software firms trying to turn them into a network.
