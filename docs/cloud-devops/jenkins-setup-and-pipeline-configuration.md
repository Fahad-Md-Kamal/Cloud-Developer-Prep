---
title: "Jenkins: Setup & Pipeline Configuration"
---

# Jenkins: Setup & Pipeline Configuration

Standing up Jenkins itself and configuring a Pipeline job, before writing any
real pipeline logic. Covers the controller/agent model, installing Jenkins,
connecting an agent over SSH, the full list of job types "New Item" offers,
and every option on a Pipeline job's own configuration screen. The real,
working pipelines built on top of this setup — credentials, Docker builds,
a full production deploy — are in
[Jenkins: Production Deployment Pipelines](jenkins-production-deployment-pipelines.md).

## Controller & Agent Model

Jenkins splits into two roles.

- The **controller** (formerly "master") serves the web UI, stores every
  job's configuration, schedules builds, and holds the plugin/credential
  state — it orchestrates, it doesn't build.
- An **agent** (formerly "slave"/"node") is a separate machine or container
  that connects to the controller and actually runs the pipeline's steps.

!!! danger "Never build directly on the controller"

    The controller has no isolation from what runs on it — a build that exhausts memory, hangs, or gets compromised takes down the one thing coordinating every other job too. Agents exist specifically to keep build workloads (arbitrary code, effectively) away from the process that everything else depends on staying up.

An agent advertises **labels** — arbitrary tags like `linux`, `docker`, or
`gpu` — and a pipeline's `agent` directive picks one by label, the same way
a Kubernetes pod picks a node by `nodeSelector`:

``` groovy
pipeline {
  agent { label 'linux && docker' }
  stages { stage('Build') { steps { sh 'make build' } } }
}
```

!!! success "Why not just one big controller"

    Separate agents mean a Windows build and a Linux build can run on the same Jenkins instance without one machine needing both toolchains installed, and adding build capacity is "add another agent," not "resize the box everything else depends on." The controller stays a stable, mostly-idle coordination point regardless of how much build traffic the team generates.

### Why agents exist, beyond just isolation

| Reason | What it actually buys |
|---|---|
| Isolation | Arbitrary, untrusted build code never runs on the one process everything else depends on. |
| Horizontal scaling | More build capacity is "provision another agent," not "give the controller a bigger instance" — capacity and coordination scale independently. |
| Environment matching | A label picks the toolchain a build actually needs — a specific OS, a GPU, a licensed tool only installed on one machine — instead of forcing every build to fit whatever the controller happens to have. |
| Parallelism | Multiple agents mean multiple builds genuinely running at once, not queued behind each other on a single executor. |
| Network/resource proximity | An agent can live inside the same VPC, region, or on-prem network as whatever it needs to reach fast — an internal artifact repo, a private database, a specific compliance boundary — without routing the controller itself into that network. |
| Team/security segregation | Folder-scoped agents (see [Security, Hardening & Production Patterns](jenkins-security-hardening-and-production-patterns.md)) let one team's builds run on infrastructure another team can't touch, without needing a separate Jenkins instance per team. |

### Types of agents

| Type | How it connects / how long it lives |
|---|---|
| Static (permanent) agent | Added once by hand via **Manage Jenkins → Nodes** and left running indefinitely — one real, named machine. Simple, but it's idle capacity paid for even when no build is using it. |
| SSH (outbound) agent | The controller initiates the connection, over SSH, to a host it already knows the address of. Needs the agent host reachable from the controller, not the other way around. |
| Inbound (JNLP/WebSocket) agent | The agent initiates the connection *to* the controller instead — the fix when the agent sits behind NAT or a firewall the controller can't reach inbound, e.g. a build machine on a laptop or in a restricted network. |
| Cloud / ephemeral agent | Provisioned on demand by a plugin (EC2 Fleet, Docker, Kubernetes) when a build needs one, then torn down afterward. No idle cost, and every build starts from a known-clean environment instead of accumulating drift on a long-lived machine. |
| Docker agent | Declared directly in a Jenkinsfile — `agent { docker { image 'node:20' } }` — a fresh, disposable container per build or per stage, with the exact toolchain version pinned in code instead of installed once on a static machine. |
| Built-in node | The controller's own, hidden executor pool — technically able to run builds itself, which is exactly what the danger box above says not to rely on. Usually set to 0 executors deliberately on any real controller. |

## Installing Jenkins & First-Time Setup

- Jenkins is a Java application — everything below assumes Java is present
  first.
- Before anything gets provisioned as code, it's worth knowing what
  "installing Jenkins" actually involves by hand.

| Method | Command | Good for |
|---|---|---|
| Native package (Amazon Linux/RHEL) | `dnf install jenkins`, after adding the Jenkins repo | A long-lived controller on a real instance |
| Native package (Debian/Ubuntu) | `apt-get install jenkins`, after adding the Jenkins `apt` repo and signing key | Same idea, different AMI family — package names don't transfer across distros |
| Docker | `docker run -p 8080:8080 -v jenkins_home:/var/jenkins_home jenkins/jenkins:lts` | Trying Jenkins locally, or running it as a container on ECS/EKS instead of a bare EC2 instance |
| WAR file | `java -jar jenkins.war` | Quick, throwaway testing — nothing installed system-wide, nothing left behind but the process |

``` bash
#!/bin/bash
# Amazon Linux / RHEL family
dnf install -y java-17-amazon-corretto
wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2023.key
dnf install -y jenkins
systemctl enable --now jenkins
```

``` bash
#!/bin/bash
# Debian / Ubuntu family
apt-get update
apt-get install -y fontconfig openjdk-17-jre
wget -O /usr/share/keyrings/jenkins-keyring.asc https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" \
  | tee /etc/apt/sources.list.d/jenkins.list
apt-get update
apt-get install -y jenkins
```

!!! note "Java version is a real compatibility constraint"

    Recent Jenkins releases require Java 17 or 21 — an older Java 11 install fails to even start the service, with the actual reason buried in `systemctl status jenkins` or `/var/log/jenkins/jenkins.log` rather than shown anywhere obvious. Check the specific Jenkins version's requirements before assuming whatever Java happens to already be on an AMI is new enough.

### First-time setup wizard

Jenkins starts on port 8080 by default and, on first boot, is locked behind
a one-time password only readable from the server itself:

``` bash
cat /var/lib/jenkins/secrets/initialAdminPassword
```

Unlock Jenkins
:   Paste that password into the setup wizard at `http://<controller-ip>:8080` — proves whoever's completing setup actually has access to the server itself, not just the network port.

Install plugins
:   "Install suggested plugins" is the reasonable default for a first controller — a curated set covering Git, pipelines, and the essentials. "Select plugins to install" is the deliberate route once plugin hygiene actually matters (see [Security, Hardening & Production Patterns](jenkins-security-hardening-and-production-patterns.md)) — smaller footprint, chosen instead of inherited.

Create the first admin user
:   Skipping this and continuing as the default `admin` account is explicitly offered but shouldn't be taken for anything beyond a five-minute local test — the same reasoning as never leaving a database on its default credentials.

Instance configuration
:   Confirms the URL Jenkins believes it's reachable at — matters later for webhook payload URLs and any notification that links back to a build, since a wrong URL here means links that go nowhere.

### Operating Jenkins as a systemd service

The native package installs Jenkins as a real systemd unit, not just a
process someone starts by hand — the same start/stop/status vocabulary as
any other Linux service applies directly:

``` bash
systemctl start jenkins      # start it now
systemctl stop jenkins       # stop it now
systemctl restart jenkins    # e.g. after a config or plugin change that needs a restart
systemctl status jenkins     # is it actually running, and since when
systemctl enable jenkins     # survive a reboot -- already done by --now during install
journalctl -u jenkins -f     # follow the service's own logs live
```

Two files control how the service actually behaves, separate from anything
configured in the Jenkins UI itself:

`/etc/sysconfig/jenkins` (RHEL family) / `/etc/default/jenkins` (Debian family)
:   Environment variables read by the systemd unit before Jenkins even starts — `JENKINS_PORT` (default 8080), `JENKINS_HOME` (where job data actually lives), `JENKINS_USER` (which OS user the process runs as). Changing the port here, not in the Jenkins UI, is what actually takes effect — the UI has no setting for its own listen port.

`JAVA_OPTS` / `JENKINS_JAVA_OPTIONS`
:   JVM flags passed to the underlying Java process — heap size (`-Xmx2g`), most commonly, since Jenkins is a long-running JVM and the default heap can be too small for a controller running many jobs.

!!! danger "A config file change needs a restart, not a reload"

    Neither of the files above is watched live — editing `JENKINS_PORT` or `JAVA_OPTS` and expecting it to take effect immediately is the same mistake as expecting a changed environment variable to reach an already-running process anywhere else. `systemctl restart jenkins` is what actually applies it.

!!! success "Verifying it actually worked"

    `systemctl status jenkins` showing `active (running)`, plus the setup wizard actually loading in a browser on port 8080, is the full confirmation — no separate health check exists beyond "does the service report running and does the UI respond."

!!! note "Provisioning this with Terraform is an infrastructure topic, not a Jenkins one"

    Wrapping this exact install script into an `aws_instance`'s `user_data`, with `JENKINS_HOME` on its own EBS volume for durability, belongs with the rest of a real Terraform resource walkthrough — that's fundamentally about provisioning compute, not Jenkins-specific configuration.

## Connecting an Agent Node via SSH

A controller with no agents attached still has nowhere to actually run a
build.

- **Manage Jenkins → Nodes → New Node** creates one — "Permanent Agent" for
  a real, long-lived machine like an EC2 instance, as opposed to a
  cloud-provisioned, one-build-and-gone agent.
- The SSH launch method needs nothing pre-installed on the target beyond
  SSH access and a working Java — the controller pushes its own agent jar
  over the connection itself.

A permanent agent node's Configure screen has these key fields (SSH launch
method, pointed at one EC2 instance):

Name
:   The node's identity inside Jenkins — shown in build history and node listings, independent of the label used to target it.

Remote root directory
:   Where the agent jar and every job's workspace get written on the remote machine, e.g. `/home/ec2-user` — also why pipeline output shows `Running on agent-one in /home/ec2-user/workspace/CICD`.

Labels
:   What a pipeline's `agent` directive actually matches against. A label can be shared across several nodes, or differ from the node's own name entirely.

Usage
:   "Use this node as much as possible" lets the controller schedule any matching job here; the alternative, "Only build jobs with label expressions matching this node," reserves it for jobs that explicitly ask for it and nothing else.

Launch method: Launch agents via SSH
:   Host and Credentials (an SSH keypair, added to Jenkins' credentials store) are all this method needs. Jenkins opens the connection itself on save, or whenever the node is manually relaunched.

### What actually happens when it connects

``` text
[SSH] Opening SSH connection to <agent-host>:22.
[SSH] Authentication successful.
[SSH] Starting sftp client.
[SSH] Copying latest remoting.jar...
[SSH] Starting agent process: cd "/home/ec2-user" && java -jar remoting.jar -workDir /home/ec2-user
Agent successfully connected and online
```

Underneath the UI, this is exactly the SSH-file-transfer-plus-remote-command
pattern behind `ssh-keygen`/`scp` fundamentals — Jenkins just automates it:
connect, copy its agent jar over SFTP, then run it with `java -jar` on the
other end.

!!! danger ""java: command not found" here means Java is missing, not Jenkins misconfigured"

    - The SSH connection and the SFTP copy can both succeed — the log shows authentication working and `remoting.jar` transferring cleanly — and the launch can still fail at the very last step: `bash: line 1: java: command not found` / `Agent JVM has terminated. Exit code=127`.
    - The cause is simply no `java` on the agent host's `PATH`.
    - A common real cause: a boot-time install script that ran `dnf install`/`yum install` without `-y` — harmless interactively, but silently skipped during a non-interactive `user_data` boot with no terminal to answer its confirmation prompt.
    - Fix on the agent host directly (install Java, or relaunch the instance with the corrected script) — nothing about this is a Jenkins-side problem.

### Referencing the node from a pipeline

``` groovy
pipeline {
    agent { label 'agent-one' }
    stages {
        stage('Hello') { steps { echo 'Hello World' } }
    }
}
```

!!! danger "An unquoted label is Groovy math, not a string"

    - `agent { label agent-one }` — no quotes — doesn't fail because of anything wrong with the label.
    - Groovy parses the bareword `agent-one` as the expression `agent - one`, subtracting two undefined variables, which throws `groovy.lang.MissingPropertyException: No such property: agent` from inside Jenkins' own `ModelInterpreter.inDeclarativeAgent`.
    - A genuinely confusing error for what's really just a missing pair of quotes.
    - `label 'agent-one'` is the fix, same as quoting any other Groovy string.

!!! note ""Still waiting to schedule task 'agent-one' is offline""

    - A pipeline whose `agent` label matches only a currently-disconnected node queues indefinitely — there's no default timeout.
    - **Manage Jenkins → Nodes →** that node shows its live status and log; clicking **Launch agent** retries the SSH connection without touching the pipeline itself.
    - An already-queued build picks up automatically the moment the node comes back online.
    - On a memory-constrained instance (a `t3.micro`'s 1GB strained by a JVM plus the remoting process), a node can connect successfully and then drop again shortly after — `dmesg | grep -i kill` on the agent host is worth checking for an OOM kill if that keeps happening.

### A node that's "online" but still fails every build

Two more failure modes worth knowing, both diagnosed on a real agent —
neither one looks like a connection problem at first, and neither one is
fixed by the "Launch agent" click above.

!!! danger "A fix applied after the agent connected doesn't apply until it reconnects"

    - Adding `ec2-user` to the `docker` group (`usermod -aG docker`) fixes the account immediately — a brand-new SSH login, or even `id ec2-user`, shows it right away.
    - But Linux fixes a process's supplementary groups at the moment it's *created*, not continuously — the agent's already-running `remoting.jar` process keeps failing with `permission denied` on `/var/run/docker.sock` forever, because it was forked before the fix existed.
    - Confirmed directly: `ps -o etime= -p <pid>` showed the process had been alive for 48 minutes, well before the group was added.
    - The fix isn't re-running the build — it's forcing a new process: **Manage Jenkins → Nodes → agent-one → Disconnect**, wait for it to show offline, *then* **Launch agent**.
    - Clicking "Launch agent" while Jenkins still considers the node connected is often a no-op, since Jenkins has no reason to kill a channel it doesn't believe is broken.

!!! note "The identical symptom, from a completely different cause, on a freshly-launched instance"

    - The same "permission denied" error can reappear on a brand-new instance too — even though `usermod -aG docker` is baked into `user_data` and should have already run.
    - The reason: `user_data` executes asynchronously in the background after boot, and SSH typically becomes reachable *before* it finishes — especially with a `yum update -y` running first, which alone can take over a minute.
    - If Jenkins' agent connects and starts its process during that window, it's fixed at the pre-`usermod` state, for a boot-timing reason rather than a manual-fix-timing reason.
    - Same fix either way: Disconnect, wait, Launch agent — by the time you're re-attempting, `user_data` has almost always finished.

!!! note ""Disk space is below threshold" when the disk isn't actually full"

    - Jenkins' built-in **Free Temp Space** monitor took an agent offline with "Only 456.59 MiB out of 456.62 MiB left on /tmp" — which reads like a full disk.
    - `df -h` on the box told a different story: `/tmp` was a `tmpfs` (RAM-backed) at 0% used, completely empty, while the real root disk had gigabytes free.
    - The catch: a `t3.micro`'s `/tmp` is sized to roughly half its 1GB of RAM — a hard ceiling around 457MB that can never satisfy the monitor's default 1GiB-free requirement, no matter how empty it is.
    - Not a leak, not real pressure — an instance-sizing mismatch against a monitor default.
    - Fixed via the small gear/settings icon on the **Manage Jenkins → Nodes** list (or **Manage Jenkins → System**'s "Free Temp Space" section): lower the threshold to something the instance can actually reach, e.g. `100MiB`.

## Job Types: What "New Item" Actually Offers

Clicking **New Item** in Jenkins shows every kind of thing it can create, in
one screen — worth knowing the full list before defaulting to whichever
one a tutorial happened to use.

| Item type | What it's for |
|---|---|
| Pipeline | Build, test, and deploy using a `Jenkinsfile`. Supports stages, parallel work, and running steps across multiple agents. |
| Freestyle project | The classic, UI-configured job type — checks out from up to one SCM, runs build steps serially, then post-build actions like archiving artifacts or sending email. Predates Pipeline-as-code, and still its own CJE exam section. |
| Multi-configuration project | One job definition run across many combinations automatically — multiple OSes, multiple environments, multiple platform targets — without hand-creating a separate job per combination. |
| Folder | A real namespace, not just a filter — two items can share a name if they live in different folders. The same folder that scopes credentials and permissions. |
| Multibranch Pipeline | Scans one repository and creates a Pipeline job per detected branch and pull request automatically — no manually creating a job per branch. |
| Organization Folder | One level up from Multibranch Pipeline — scans an entire GitHub org/Bitbucket project for repositories, and creates a Multibranch Pipeline for each one it finds. |

!!! note ""Duplicate an existing item" isn't a type"

    It's the seventh option on the same screen, but it's a shortcut action, not a job type of its own — it just copies an existing item's configuration into a new one, for any type above, as a starting point instead of configuring from scratch.

## Pipeline Job Configuration: General, Triggers & the Script Definition

Choosing "Pipeline" as the item type opens this configuration screen — the
same shape every Pipeline job shares, regardless of what its stages
actually do.

### General

| Option | What it actually does |
|---|---|
| Discard old builds | A retention policy — keep only the last N builds or the last N days. Without it, build history grows forever. |
| Do not allow concurrent builds | Serializes runs of *this same job* — a second trigger waits instead of running in parallel. For a job that touches shared state it can't safely share with itself. |
| Do not allow the pipeline to resume if the controller restarts | Jenkins normally tries to resume an in-progress pipeline after a controller restart. Disabling this makes a restart abort the run instead — the right choice when a resumed run risks replaying a non-idempotent step. |
| GitHub project | Just a display link back to the repo's GitHub page — cosmetic, not functional. |
| Pipeline speed/durability override | Trades how often Jenkins persists pipeline state to disk against I/O overhead — safer and slower, or faster and more state lost if the controller crashes mid-run. |
| Preserve stashes from completed builds | A `stash` (files passed between stages/agents) is normally discarded once the build finishes — this keeps it around afterward for inspection. |
| This project is parameterized | The UI equivalent of a Jenkinsfile's `parameters {}` block — configured by clicking instead of by code. |
| Throttle builds | Rate-limits how often, or how many concurrently, this job (or a named category of jobs) can run — for protecting a shared resource several different jobs compete for. |

!!! danger "Concurrent-build prevention and throttling solve different problems"

    "Do not allow concurrent builds" only stops *this one job* from overlapping with itself. "Throttle builds" limits a whole category of jobs against each other — useful when five unrelated jobs all hit the same rate-limited API and none of them individually looks like the problem.

### Triggers

| Trigger | What starts the build |
|---|---|
| Build after other projects are built | Upstream/downstream chaining — this job runs automatically once a named other job finishes. |
| Build periodically | A cron-syntax schedule, evaluated in the controller's own timezone. |
| GitHub hook trigger for GITScm polling | The real webhook — GitHub pushes an event to Jenkins the moment something happens, no delay. |
| Poll SCM | The older mechanism — also cron-syntax, but Jenkins checks the repo on a timer instead of being told immediately. |
| Trigger builds remotely | An authenticated URL with a token, callable by an external script or system to start a build without needing full Jenkins API credentials. |

### Scheduling a pipeline: `triggers { cron(...) }` in the Jenkinsfile itself

"Build periodically" in the table above configures a schedule through the
UI — a Jenkinsfile can declare the identical schedule as code instead, in
the same `triggers {}` block later used for GitHub-hook triggering:

```groovy
pipeline {
    agent { label 'agent-one' }
    triggers {
        cron('H 2 * * *')
    }
    stages {
        stage('Nightly check') {
            steps { echo 'Runs once a day, somewhere around 2am' }
        }
    }
}
```

- A schedule written into the Jenkinsfile is checked into git, reviewable,
  and travels with the branch — a Multibranch Pipeline (see
  [Security, Hardening & Production Patterns](jenkins-security-hardening-and-production-patterns.md))
  can even give a feature branch its own, different schedule.
- A schedule set only through the UI's "Build periodically" checkbox is
  invisible to anyone reading the repo.

### Cron syntax, and Jenkins' one real addition to it

Five fields, the same order as a standard crontab:

```
MINUTE  HOUR  DOM  MONTH  DOW
0       2     *    *      *        → 02:00 every day
*/15    *     *    *      *        → every 15 minutes
0       9-17  *    *      MON-FRI  → hourly, 9am-5pm, weekdays only
```

**`H` (hash) — Jenkins' own addition, and the one actually worth using:**

- `H 2 * * *` looks like "2am," but `H` isn't a fixed value — it's a hash
  of the job's own name: deterministic (the same job always lands on the
  same minute every time), but spread across the full range for
  *different* jobs.
- Written as `0 2 * * *`, a hundred jobs on one Jenkins instance can all be
  scheduled for exactly 02:00:00, all firing on the same controller and
  agents at once.
- `H 2 * * *` spreads those same hundred jobs across the whole 02:00–02:59
  hour instead, without anyone hand-picking a different minute for each
  one.
- `H` can also scope a narrower range — `H(0-29) * * * *` picks a
  consistent minute somewhere in just the first half of every hour.

**Timezone:**

- Evaluated in the controller's own configured system timezone by default.
- Override it per-trigger by putting a `TZ=` line first, on its own line
  inside the same string: `cron('TZ=Asia/Dhaka\nH 2 * * *')`.

### The part usually actually wanted: check-then-act, not just "run on a timer"

A schedule alone only starts a pipeline — most real scheduled jobs still
need to *decide* whether there's anything to actually do once they wake up,
rather than unconditionally repeating an action every single time. A
nightly Terraform drift check is the clearest example:

```groovy
pipeline {
    agent { label 'agent-infra' }
    triggers { cron('H 2 * * *') }
    stages {
        stage('Check for drift') {
            steps {
                script {
                    sh 'terraform init'
                    def exitCode = sh(script: 'terraform plan -detailed-exitcode', returnStatus: true)
                    if (exitCode == 2) {
                        echo 'Drift detected -- infrastructure no longer matches the .tf files'
                        // notify, or gate a follow-up apply, here
                    } else if (exitCode == 0) {
                        echo 'No drift -- infrastructure matches state exactly'
                    } else {
                        error('terraform plan itself failed')
                    }
                }
            }
        }
    }
}
```

- `terraform plan -detailed-exitcode`'s exit codes are exactly this
  check-then-act signal: `0` means no changes needed, `2` means changes
  were detected (drift, or a `.tf` file that hasn't been applied yet), `1`
  means the plan itself errored.
- The schedule (`triggers { cron(...) }`) is what makes this run every
  night unattended.
- The exit-code branch is what makes it *only* act — notify, open a
  ticket, gate a follow-up `apply` — when there's actually something to
  act on, instead of sending a "checked, all fine" notification every
  single night regardless.

!!! success "The same shape as every other conditional gate in this material"

    Reacting to `terraform plan`'s exit code here is the identical idea as a `when { changeset ... }` guard on a registry-push pipeline (see [Security, Hardening & Production Patterns](jenkins-security-hardening-and-production-patterns.md)) or a canary's metrics-check gate (see [CI/CD & Progressive Delivery](cicd-and-progressive-delivery.md)) — a scheduled pipeline still checks a real condition before doing anything consequential; the schedule just decides *when* to check, not *whether* the check passed.

!!! note "`pollSCM` is the same cron syntax, for a narrower, git-specific check"

    `triggers { pollSCM('H/5 * * * *') }` uses this identical cron string format, but its built-in condition is always "did the repository get new commits since last time" — Jenkins checks the repo on the given schedule and only actually starts a build if something changed. A plain `cron(...)` trigger has no built-in condition at all — it fires every time, on schedule, and it's on the pipeline itself (like the Terraform exit-code check above) to decide whether there's anything worth doing once it does.

### The script definition itself

Further down the same screen, "Pipeline script" is one of two ways to tell
Jenkins what to actually run:

``` groovy
pipeline {
    agent any

    stages {
        stage('Hello') {
            steps {
                echo 'Hello World'
            }
        }
        stage('Create Folder') {
            steps {
                sh "mkdir -p devops"
            }
        }
        stage('Bye') {
            steps {
                echo 'Bye'
            }
        }
    }
}
```

!!! danger "This is the opposite of what a real Jenkinsfile setup recommends"

    - "Pipeline script" types the Groovy directly into this one field, saved only in Jenkins' own job configuration — invisible to git history, code review, or branch-per-Jenkinsfile discovery.
    - "Pipeline script from SCM" is the other option on the same dropdown — pointing at a `Jenkinsfile` checked into the repository, which is what every real pipeline in [Jenkins: Production Deployment Pipelines](jenkins-production-deployment-pipelines.md) assumes.
    - Fine for a five-minute "does Jenkins work at all" test; the wrong choice for anything meant to last.

Use Groovy Sandbox
:   Checked by default — restricts which Java/Groovy APIs a script can call, since arbitrary unrestricted Groovy can do real damage running on the controller. Unchecking it requires an administrator to manually approve the script before it can run.

Pipeline Syntax (link)
:   A built-in generator that produces correct step syntax by filling out a form, instead of memorizing every step's exact arguments from documentation.
