# Podping and Pingslurp

*Podping* is a distributed system, initiated by the [PodcastIndex](https://podcastindex.org)
for sending out alerts whenever a podcast changes. These dashboard provide some insight into
the current health of the system via a monitoring tool called *Pingslurp*.

## RC Overview

This group of graphs shows the Resource Credit (RC) health of
the Podping infrastructure behind [podping.cloud](https://podping.cloud).

The *Delegating Accounts* are ones which can be used to send Resource Credits to
the *Receiving Accounts* which are the ones actively sending Podpings.

## Graphs

- Blue line is the current RC % of the account (right scale).
- Red line is the absolute value of the RC's on the account (left scale).
- A vertical dashed line indicates that an RC delegation was either increased or decreased.

An automated system maintains the RC's of the receiving accounts between 25% and 40%.