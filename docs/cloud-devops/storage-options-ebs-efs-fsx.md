---
title: "Storage Options: EBS, EFS, FSx & Data Transfer"
---

# Storage Options: EBS, EFS, FSx & Data Transfer

[S3 Deep Dive](storage-and-observability.md#s3-deep-dive) covers object
storage. This page covers the storage an EC2 instance actually attaches
to — block, file, and specialized — plus the services that move large
amounts of data into or out of AWS.

## EBS vs EFS vs FSx vs Instance Store

| | EBS | EFS | FSx | Instance Store |
|---|---|---|---|---|
| Type | Block storage | File storage (NFS) | File storage (Windows/Lustre-specific) | Block storage |
| Attaches to | One instance at a time (one exception: Multi-Attach for specific volume types) | Many instances at once, across AZs | Many instances at once | Physically on the host, one instance |
| Persists past instance stop/termination | Yes | Yes | Yes | **No** — wiped on stop or termination |
| Scales | Manually resize the volume | Automatically, no provisioning | Provisioned, or auto-scaling depending on type | Fixed, tied to instance type |
| Use for | A database's root/data volume — needs to be attached to exactly one instance | A shared directory many instances read/write at once (content management, shared home directories) | Windows file shares (FSx for Windows File Server) or HPC workloads (FSx for Lustre) | Scratch space, cache, temporary data an instance can afford to lose |

!!! danger "Instance Store data is gone the moment the instance stops"

    Instance Store volumes are physically on the host machine — stop
    (not just reboot) or terminate the instance, and the data is
    unrecoverable. Never a fit for anything that needs to survive past
    the instance's own lifecycle; that's exactly what EBS is for.

!!! success "The exam signal"

    "A shared file system, read/written by many EC2 instances at once"
    → EFS, not multiple EBS volumes (EBS can't do that — Multi-Attach is
    the narrow exception, not the default). "Fastest possible scratch
    disk, data loss on stop is acceptable" → Instance Store. "Windows
    file share" or "HPC/machine learning training needing extreme
    throughput" → FSx (for Windows File Server, or Lustre, respectively).

## Moving Data Into and Out of AWS

`Storage Gateway`
:   A hybrid storage appliance (virtual machine or hardware) that lives
    on-premises and presents AWS storage (S3, EBS snapshots) as a local
    file share, volume, or tape library — so on-premises applications
    keep working unmodified while their data actually lives in AWS.
    Three types: **File Gateway** (NFS/SMB share backed by S3),
    **Volume Gateway** (iSCSI block storage, cached or stored locally),
    **Tape Gateway** (a virtual tape library for backup software that
    still expects physical tapes).

`Snow Family`
:   Physical devices for moving very large amounts of data where network
    transfer would be too slow or too expensive — AWS ships you a
    device, you load it with data (or it loads data from AWS, for
    edge-to-cloud or disconnected use), you ship it back.

    - **Snowcone** — smallest, a few terabytes, can also run compute at
      the edge.
    - **Snowball Edge** — tens of terabytes, with onboard compute
      options for edge processing before shipping.
    - **Snowmobile** — an actual shipping container on a truck, for
      exabyte-scale migrations.

`DataSync`
:   Automated, ongoing data transfer and sync between on-premises
    storage (or another cloud) and AWS (S3, EFS, FSx) **over the
    network** — not physical shipping. Handles the scheduling,
    encryption in transit, and incremental/delta transfers automatically.

!!! success "The exam signal"

    The deciding question is almost always **"how much data, and is the
    network fast enough to move it in the time available."** A few
    hundred GB to a few TB, ongoing → DataSync. Tens of TB to PB, network
    transfer would take weeks → Snowball Edge. Exabyte-scale → Snowmobile.
    An on-premises app needs to keep working against local storage,
    unmodified, while the data lives in AWS → Storage Gateway.
