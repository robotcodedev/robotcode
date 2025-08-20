# Security Policy

> This policy applies to all public projects under the **robotcodedev/robotcode** repository, including the Python packages on PyPI, the VS Code extension, and the JetBrains plugin.

## Reporting a Vulnerability

**Please do not open public issues for security problems.**

### Preferred Reporting Methods

**Primary:** Use GitHub's **Private Vulnerability Reporting** on this repository:
* Go to the repository's **Security** tab → **Report a vulnerability**
* Creates a private, secure thread with the maintainers
* Automatically tracks communication and resolution

**Alternative:** Email [security@robotcode.io](mailto:security@robotcode.io)
* This address is actively monitored by the maintainer team
* PGP encryption available upon request (key ID: `99B8D6B0`)
* If this address is unavailable, contact the maintainer via the email listed in the latest release notes

### Required Information

When reporting, please include:

* **Component**: Affected component (Language Server, Debug Adapter, CLI, VS Code extension, JetBrains plugin, specific PyPI package and version)
* **Description**: Clear description of the vulnerability and attack vector
* **Impact**: Potential impact and your severity assessment (CVSS score welcome)
* **Reproduction**: Steps to reproduce, proof of concept, or minimal repro project
* **Environment**: OS, Python/Robot Framework versions, editor/IDE version
* **Mitigations**: Any known workarounds or temporary fixes

We also accept **supply-chain reports** (malicious dependencies, typosquats, unsafe defaults) affecting RobotCode.

## Our Response Commitments

### Standard Timeline
* **Triage acknowledgement:** within **3 business days**
* **Initial assessment:** within **7 days** we'll confirm scope, assign severity (CVSS score), and provide timeline for resolution
* **Regular updates:** every **14 days** on progress for confirmed vulnerabilities
* **Fix target:** within **90 days** for high/critical issues, next regular release for medium/low severity issues

### Critical Vulnerability Fast-Track
For **critical vulnerabilities** (CVSS 9.0+, active exploitation, or RCE):
* **Acknowledgement:** within **24 hours**
* **Assessment:** within **48 hours**
* **Emergency release:** within **14 days** when feasible

### Coordinated Disclosure
* **Standard disclosure timeline:** 90 days after fix release, or by mutual agreement
* We'll coordinate with you on public disclosure timing
* Please **do not disclose** details publicly until we publish an advisory/release with a fix
* We may request extended timeline for complex fixes requiring upstream coordination

## Severity Classification

We use **CVSS v4.0** (v3.1 also accepted) with the following guidelines:

| Severity | CVSS Score | Examples |
|----------|------------|----------|
| **Critical** | 9.0-10.0 | Remote Code Execution, Privilege Escalation without user interaction |
| **High** | 7.0-8.9 | RCE requiring user interaction, Authentication bypass, Sensitive data exposure |
| **Medium** | 4.0-6.9 | Local privilege escalation, Limited information disclosure, DoS |
| **Low** | 0.1-3.9 | Minor information leakage, UI spoofing |

## Scope

### In Scope ✅
* RobotCode Python packages and modules (language server, debug adapter, CLI)
* RobotCode VS Code extension
* RobotCode JetBrains plugin
* Documentation site content that could cause vulnerabilities in above components
* Supply chain issues (malicious dependencies, typosquatting)
* Configuration defaults that create security risks

### Out of Scope ❌
* **Robot Framework** core and standard libraries (report to Robot Framework project)
* Third-party dependencies unless there's a vulnerable usage pattern within RobotCode
* Issues requiring unrealistic attack scenarios (e.g., running arbitrary untrusted Robot tests in production without sandboxing)
* Social engineering attacks against project maintainers
* Physical access scenarios

## Supported Versions

**RobotCode Versions:**
* **Latest stable release** of all RobotCode packages/extensions receives full security support
* **Previous major version** may receive critical security backports at maintainer discretion
* **Older versions** are out of security support

**Dependencies & Requirements:**
* **Minimum requirements**: Python 3.10+ and Robot Framework 5.0+
* **Dependency security**: Python and Robot Framework have their own security policies and support lifecycles
* **Out of scope**: Security issues in Python/Robot Framework should be reported to their respective projects
* **Compatibility**: We may drop support for end-of-life Python/Robot Framework versions without prior notice

Current releases: [GitHub Releases](https://github.com/robotcodedev/robotcode/releases)

## CVE Assignment & Advisories

* We assess severity using **CVSS v4.0** (Base score + Threat/Environmental when applicable)
* **CVEs** will be requested for vulnerabilities with CVSS ≥ 7.0 or significant user impact
* **GitHub Security Advisories** will be published describing impact, affected versions, and remediation
* All advisories include the **CVSS vector** and detailed mitigation steps

## Recognition & Responsible Disclosure

### Credit Policy
Unless you request otherwise, we will:
* Credit reporters by name or handle in security advisories
* Mention contributors in release notes

### Responsible Disclosure Incentives
While we don't offer monetary rewards, we provide:
* Public recognition and attribution
* Direct communication channel with maintainers for future research
* Conference speaking opportunity referrals when appropriate

## Safe Research Guidelines

✅ **Encouraged:**
* Testing in isolated environments
* Responsible proof-of-concept development
* Coordinating with our team before public research

❌ **Prohibited:**
* Data destruction, exfiltration, or privacy violations
* Testing against production systems of other users
* Spam, DoS, or aggressive automated scanning
* Social engineering attempts against maintainers or users

## Security Hardening for Users

### Development Environment
* **Workspace Trust**: Only open trusted workspaces; Language Server features can execute project code
* **Virtual Environments**: Use isolated Python environments for Robot Framework projects
* **Dependency Management**: Pin dependency versions and regularly audit for known vulnerabilities

### Production Use
* **Code Review**: Treat Robot Framework test suites as code - review before execution
* **Sandboxing**: Run untrusted tests in containerized or sandboxed environments
* **Access Control**: Limit file system access for automated test execution

### Updates
* Keep Python, Robot Framework, and RobotCode extensions up to date
* Subscribe to GitHub security advisories for notifications
* Monitor release notes for security-related changes

## Legal

This security policy is subject to change. Current version available at: [https://github.com/robotcodedev/robotcode/security/policy](https://github.com/robotcodedev/robotcode/security/policy)

By participating in our security research program, you agree to:
* Follow responsible disclosure practices
* Comply with applicable laws and regulations
* Respect user privacy and data protection requirements

---

**Thank you for helping keep RobotCode and its users secure!**

*Last updated: 2025-08-20*
*Version: 1.0*