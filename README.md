# dev-conventions

The working conventions shared by Gunnar Hilling's repositories, so that a fix reaches every one
of them instead of one copy. It started with
[ai-assisted-todolist](https://github.com/guhilling/ai-assisted-todolist) (TaskFest) and
hilling-it-website; [ai-assisted-todolist#400](https://github.com/guhilling/ai-assisted-todolist/issues/400)
says what is shared and why.

## check-doc-references

A GitHub Action that fails when a file in the repository names a documentation page under `doc`
that does not exist: a code comment, an OpenTofu file, a CLAUDE.md or a workflow. Those are prose,
not links, so nothing else notices when the page they name moves.

```yaml
- uses: actions/checkout@v7
- uses: guhilling/dev-conventions/check-doc-references@<commit sha> # v1.0.0
  # Optional: prefixes to leave alone, one per line, such as generated files.
  with:
    exclude: |
      doc/api/
```

It checks the repository checked out at the workspace's root, as `actions/checkout` does without
a `path`. A reference is `doc` followed by a path ending in `.md`, or by a chapter directory with its
trailing slash. Only files git tracks are read.

To run it locally, from anywhere inside the repository:

```sh
curl -fsSL https://raw.githubusercontent.com/guhilling/dev-conventions/v1.0.0/check-doc-references/check_doc_references.py | python3 - --exclude doc/api/
```

## Renovate preset

`default.json` is the Renovate policy the repositories share: weekly pull requests before 6am on
Monday (Berlin), patch and minor updates merging themselves once every check is green, and majors
waiting for a human. A repository extends it and adds only its own rules on top:

```json
{
  "extends": ["github>guhilling/dev-conventions#v1.1.0"]
}
```

Pinned to a tag, Renovate's `renovate-config` manager opens the pull request that moves the
repository to a newer one.

`platformAutomerge` is off on purpose: without a ruleset that requires status checks, GitHub's
own auto-merge would merge before anything had run. The schedule restricts when pull requests are
opened, not when they merge, and Renovate can also be started from the Mend dashboard, so activity
outside it is expected.

## The `conventions` plugin for Claude Code

This repository is also a Claude Code plugin marketplace, `dev-conventions`, with one plugin,
`conventions`. It holds what the repositories' `CLAUDE.md` files used to repeat:

- **The shared rules**, [`plugins/conventions/rules.md`](plugins/conventions/rules.md): asking
  instead of guessing, the pull request workflow and its reviews, branches, `/doc` and its
  chapters, secrets, Renovate, issues, TDD and existing tests. A SessionStart hook prints the file,
  and Claude Code adds what a SessionStart hook prints to the session's context, so the rules are
  always there: at startup, after `/clear` and after a compaction. A resumed session keeps the copy
in its transcript, so the hook does not print a second one. A plugin cannot carry
  a `CLAUDE.md` of its own, and a skill would be loaded only when Claude decides it is relevant.
  Claude Code takes at most 10,000 characters from a hook this way, and a test holds the file
  under that.
- **Two guards**, as PreToolUse hooks that refuse a command with exit status 2, or ask Gunnar
  first where a change is sometimes wanted:
  - `keep-git-hooks.py` refuses commands that skip, switch off or write over a repository's
    `.githooks` (such as `git push --no-verify`, a change to `core.hooksPath`, or `cp`, `tee` or
    `sed -i` onto a hook). Claude's own Write and Edit onto a hook ask instead, since that is how
    a hook is changed in a pull request.
  - `plan-only.py` refuses OpenTofu or Terraform commands that change infrastructure or its state,
    `tofu init -force-copy` and `tofu workspace select -or-create` included. TaskFest's
    `env.sh up`, `down` and `account`, which apply after showing their plan, ask instead. Text
    that git or the GitHub CLI only stores, such as a commit message or a pull request's body, is
    not read as a command, unless the shell would expand something in it.

  Both match text rather than parse the shell, on purpose: a false alarm costs a reworded command,
  a miss an apply. One of each is accepted (ai-assisted-todolist#470): a here-document with an
  unquoted delimiter is read as commands even when it is a commit message, because the shell
  expands what is in it; and a hook written over by something neither guard knows, a script for
  one, still gets past them. The
  `main-branch` ruleset on GitHub is what keeps a push from `main` in the end. The
  `.githooks/pre-push` they protect stays in each repository that has one, because git runs a hook
  from a fixed path and the plugin's path changes with every version.

The repository's own `CLAUDE.md` keeps its own rules and names what the shared ones leave to it,
such as its GitHub project. Where the two disagree, the repository's `CLAUDE.md` wins.

A repository turns the plugin on in its committed `.claude/settings.json`, pinned to a tag:

```json
{
  "extraKnownMarketplaces": {
    "dev-conventions": {
      "source": {
        "source": "github",
        "repo": "guhilling/dev-conventions",
        "ref": "v1.2.0"
      }
    }
  },
  "enabledPlugins": {
    "conventions@dev-conventions": true
  }
}
```

`claude plugin marketplace add guhilling/dev-conventions#v1.2.0 --scope project` writes the first
half. The plugin is listed by a relative path inside the marketplace, so once someone has trusted
the folder, Claude Code loads it from the marketplace's checkout without a separate install. The
plugin sets no `version`, so its version is the commit the tag names. Renovate has no manager for
this pin, so each repository moves it with a regex manager:

```json
{
  "customType": "regex",
  "managerFilePatterns": ["/^\\.claude/settings\\.json$/"],
  "matchStrings": ["\"repo\":\\s*\"(?<depName>guhilling/dev-conventions)\",\\s*\"ref\":\\s*\"(?<currentValue>v[^\"]+)\""],
  "datasourceTemplate": "github-tags"
}
```

**Cloud sessions do not get the plugin.** A session on claude.ai/code does not install the plugins
a repository's `.claude/settings.json` declares: adding a marketplace from a repository waits for
the workspace trust dialog, which a cloud session never shows ([what carries over to a cloud
session](https://code.claude.com/docs/en/cloud-environments#what-carries-over-from-your-setup)).
Such a session has the repository's `CLAUDE.md` and the hooks in its own `.claude/settings.json`,
but neither the shared rules nor the two guards. That is what the documentation says; it has not
been tried in a cloud session.

The tests run with:

```sh
python3 -m unittest discover -s plugins/conventions/hooks -p 'test_*.py'
```

and `claude plugin validate .` checks the manifests; CI runs both. To try a change before it is
tagged, start Claude Code with `--plugin-dir plugins/conventions`.

## Releases

A release is a lightweight tag `vX.Y.Z` on `main`, without a GitHub Release. A fix is a patch,
anything a caller has to change for is a major. Callers of the action pin the commit SHA with the
tag in a comment; the plugin is pinned by the tag itself, because `.claude/settings.json` has no
comments to carry it. Either way Renovate opens the pull request that moves them to a new tag.

## License

Apache-2.0, see [LICENSE](LICENSE).
