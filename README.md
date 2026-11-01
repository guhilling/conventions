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

## Releases

A release is a lightweight tag `vX.Y.Z` on `main`, without a GitHub Release. A fix is a patch,
anything a caller has to change for is a major. Callers pin the commit SHA with the tag in a
comment, and Renovate opens the pull request that moves them to a new tag.

## License

Apache-2.0, see [LICENSE](LICENSE).
