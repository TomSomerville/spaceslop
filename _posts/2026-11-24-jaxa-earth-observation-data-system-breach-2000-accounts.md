---
title: "JAXA says hackers breached a satellite weather data portal, exposing about 2,000 accounts"
date: 2026-11-24 06:10:00 +0000
summary: "Japan's space agency took an Earth observation data distribution system offline after an intruder installed a backdoor and took account names and encrypted passwords of roughly 2,000 users."
category: policy
story_key: jaxa-earth-observation-system-breach
sources:
  - name: JAXA
    title: "Report on Information Leakage Following Unauthorized Access to an Earth Observation Data Distribution System"
    url: https://global.jaxa.jp/press/2026/11/20261124-2_e.html
  - name: JAXA (Japanese original)
    title: "Earth observation data distribution system unauthorized access report"
    url: https://www.jaxa.jp/press/2026/11/20261124-2_j.html
---

The Japan Aerospace Exploration Agency has disclosed a cyber intrusion into a public-facing system that distributes precipitation and weather data from Earth observation satellites. According to the agency's Japanese-language report, published on 24 November, the attacker took account names and encrypted passwords belonging to about 2,000 users.

JAXA says the intruder exploited a command injection flaw in part of the system's web application, then installed a backdoor and attempted to scan the network and pull out information. The system is run by the agency's Earth Observation Research Center and its Satellite Applications Operations Center.

## Timeline

Suspicious activity began on 18 November, six days before the public notice. That morning, network scanning was seen coming from the web server. In the afternoon, an unrecognised account appeared on an authentication server, and login attempts against a network switch failed. JAXA says it confirmed the intrusion the same day, shut the web server down by 16:30 and halted the FTP server as a precaution by 19:30.

The agency says the satellite observation data held on the system is public and that there is no sign it was accessed. The credential data is the part JAXA treats as compromised.

## What happens next

The system has been disconnected from the network and remains offline, with no restoration date given. JAXA says it has largely determined the scope and cause of the breach, is removing the backdoor, and is fixing the vulnerability. It is also checking the rest of the web application for similar flaws. Affected users will be notified individually, and the agency warned the public to watch for phishing emails that impersonate JAXA. It said it will publish further findings as they emerge.

## Why it matters

The affected system handles open weather and precipitation data rather than spacecraft operations, and JAXA's account does not suggest any link to flight systems. Still, it adds to a short list of space-agency IT incidents, and JAXA has had to deal with cyber incidents before. For users who reused a password elsewhere, even encrypted credentials are a reason to change them. The English page JAXA published for the notice carries only a title and the date and says the full text is Japanese only, so details here come from the Japanese original.
