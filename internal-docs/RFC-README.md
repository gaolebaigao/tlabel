# TLabel RFC Process

## Overview

TLabel uses a Request for Comments (RFC) process for all significant changes to the format specification. This ensures the community has a voice in the evolution of the standard.

## When to Write an RFC

An RFC is required for:
- Adding, removing, or renaming dimensions in `tlabel_v2`
- Changing the JSON schema structure
- Modifying cascade rules
- Introducing new export format converters
- Any breaking change to the file format

An RFC is **not** required for:
- Bug fixes
- Performance improvements
- UI changes
- Internal refactoring that doesn't affect the output format

## RFC Template

See [RFC-TEMPLATE.md](RFC-TEMPLATE.md) for the template.

## Process

1. **Draft**: Copy the template, fill in your proposal. Submit as a PR to `docs/rfc/`.
2. **Review**: Community reviews the RFC. Author addresses feedback.
3. **Final Comment Period (FCP)**: Once consensus is reached, a 7-day FCP begins.
4. **Decision**: Core maintainers merge (accepted) or close (rejected) the PR.
5. **Implementation**: Accepted RFCs are implemented and included in the next release.

## RFC Status

| Status | Meaning |
|--------|---------|
| Draft | Under discussion |
| FCP | Final Comment Period (7 days) |
| Accepted | Approved, implementation in progress |
| Merged | Implemented and released |
| Rejected | Not accepted |
| Superseded | Replaced by a newer RFC |
