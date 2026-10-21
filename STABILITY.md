# Stable contract

`1.0.0` is this group's first stable version. Each group evolves independently after this release; component Skill metadata records the stable distribution in which it is maintained. Earlier 0.x numbers are development or preview identities, not additional stable releases.

The public compatibility surface is the declared Skill IDs and membership, documented task boundaries, supplied command-line interfaces and machine-readable schema contracts. Preserve existing meanings, fail closed on unsupported schemas and document migrations. Generated prose and presentation layout are task-dependent outputs, not a byte-stable API. Native software, external tools and client capabilities retain their own requirements.

Use PATCH for compatible defect corrections, MINOR for compatible additions, and MAJOR for incompatible membership, identity, CLI, schema or required-behavior changes. Internal review rounds are recorded separately from SemVer. The final GitHub tag is `v1.0.0`; an internal `r1` directory is a review coordinate, not a second stable version. Candidate status remains separate from publication status.

Published release bytes and tags are immutable. Later fixes receive a new version. A passed package check is not a promise of automatic activation, scientific truth, native application compatibility or successful external publication.

Version semantics follow [Semantic Versioning 2.0.0](https://semver.org/).
