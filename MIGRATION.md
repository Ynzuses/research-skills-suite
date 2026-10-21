# First stable grouping

The former eight-Skill research package mixed general science, genomics and project infrastructure. Stable distributions are now selected by user goal. Skill IDs and schema versions are preserved; only their owning group changes where shown.

| Previous package | Skill or responsibility | Stable owning group |
| --- | --- | --- |
| research-skills-suite (0.x) | evidence, scientific writing, reproducible computation, research coordination | research-skills-suite |
| research-skills-suite (0.x) | genomics-study-design; genotype-imputation-benchmarking | genomics-skills-suite |
| research-skills-suite (0.x) | manage-workspace-memory | workspace-skills-suite |
| git-workspace-closeout (0.x) | git-workspace-closeout | workspace-skills-suite |
| research-skills-suite (0.x) | research-document-delivery | office-authoring-suite |
| office-authoring-suite (0.x) | word-authoring; powerpoint-authoring; excel-authoring | office-authoring-suite |
| voice-preserving-writing (0.x) | voice-preserving-writing | voice-preserving-writing |
| targeted-resume (0.x) | targeted-resume | targeted-resume |

Published `v0.6.0` remains a historical preview. Local 0.7–0.9 research iterations and the other groups' 0.x candidates are retained as pre-stable history; they are not silently relabeled or overwritten.

Before upgrading, inspect active installations across agent/plugin discovery roots. Compare any local changes with the new owning release and retain a recoverable backup outside discovery. Replace each complete Skill once, so the same ID is not active from both an old all-in-one package and a new group. Installation and removal remain explicit operations; this package does not automatically migrate an existing installation.

`research-document-delivery` keeps its historical ID. Its stable scope includes professional and academic rich documents; scientific evidence methods are optional and topic-dependent. Word creates ordinary new documents; document delivery owns preservation-sensitive revisions and final validation.

The two teaching/learning methods are not bundled in these six groups. Third-party Skills mentioned as examples retain their own distribution and license identities.
