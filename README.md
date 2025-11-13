[![Build Status](https://travis-ci.org/elight/acts_as_commentable_with_threading.png)](https://travis-ci.org/elight/acts_as_commentable_with_threading)
[![Code Climate](https://codeclimate.com/github/elight/acts_as_commentable_with_threading/badges/gpa.svg)](https://codeclimate.com/github/elight/acts_as_commentable_with_threading)

Infrastructure Automation Toolkit (Python)
==========================================

The current focus of this repository is a Python-based automation agent that
scans on-premises infrastructure, snapshots critical artefacts, and records
everything it discovers into an encrypted vault.  The agent ships with an
optional HTTP dashboard to surface step-by-step execution details and estimated
timings so operators can monitor long-running tasks without tailing logs.

The toolkit intentionally avoids third-party dependencies to simplify
distribution across heterogeneous data centre fleets.  Python 3.10 or newer is
required, and the package can be executed directly or bundled into a Docker
image for easy deployment on bastion hosts and jump boxes.

At a glance the automation agent provides:

* Inventory collectors for environment variables and host facts that export
  JSON artefacts for downstream tooling.
* Vault storage that encrypts discovered secrets with a symmetric key supplied
  via environment variable.
* Pluggable backup targets that archive files or directories to rotation-aware
  local storage.
* Structured logging and dashboard endpoints to surface task progress in real
  time.

Quick Start
-----------
1. Ensure Python 3.10+ is installed and activate a virtual environment if
   desired.
2. Copy `config/infrastructure_agent.yml` and customise collectors, vault, and
   backup targets to match your environment.
3. Export a base64-encoded 32-byte key for the vault encryption layer:

       export INFRA_AGENT_VAULT_KEY="$(python - <<'PY'
from secrets import token_bytes
import base64
print(base64.b64encode(token_bytes(32)).decode())
PY
)"

4. Launch the agent with your configuration:

       python -m infrastructure_agent.cli --config config/infrastructure_agent.yml

Pass `--dashboard` to expose a JSON status endpoint (default
`0.0.0.0:8020/status`) and `--dump-status` to print a full run summary when the
agent exits.

---

Toolkit Details
---------------
The following sections dive deeper into the Python automation toolkit, covering configuration options, observability features,
testing guidance, and container packaging tips.  It is designed to run on any host that has Python 3.10 or newer available and
can optionally expose an embedded HTTP dashboard for observability.

### Features

* Inventory collectors for environment variables and basic host facts stored under `inventory/` in the working directory.
* A minimal vault service that encrypts secrets with a symmetric key sourced from an environment variable before persisting
  them to disk.
* Backup targets that archive configurable directories or files to rotation-friendly local storage.
* Structured logging and a JSON dashboard endpoint to follow agent progress step-by-step.

### Quick start

1. Ensure Python 3.10+ is available (a virtual environment is recommended for development).
2. Copy `config/infrastructure_agent.yml` and tailor the collectors, vault, and backup sections to your infrastructure.
3. Export a base64-encoded 32-byte key for the vault, for example:

       export INFRA_AGENT_VAULT_KEY="$(python - <<'PY'
from secrets import token_bytes
import base64
print(base64.b64encode(token_bytes(32)).decode())
PY
)"

4. Run the agent:

       python -m infrastructure_agent.cli --config config/infrastructure_agent.yml

Pass `--dashboard` to also expose an HTTP endpoint (default `0.0.0.0:8020/status`) that returns the latest task state as JSON.
Use `--dump-status` to print a complete status snapshot to STDOUT when the run completes.

### Configuration structure

The sample configuration demonstrates the supported keys:

* `runtime` – Defines the working directory for generated files, the log destination, and optional dashboard host/port values.
* `inventory.collectors` – Ordered list of discovery plugins.  The built-in `environment` collector exports specific variables,
  while the `host` collector captures the hostname and platform data.
* `vault` – Enables secret storage, selects the filename for encrypted data, and specifies the environment variable that carries
  the encryption key (base64 encoding is supported out of the box).
* `backups.targets` – Declares backup destinations.  The provided `local` target can archive directories into timestamped tarballs
  and applies configurable retention policies.

### Observability and logs

Logs are written to the file defined in `runtime.log_file` and summarised on STDOUT when the agent exits.  When the dashboard is
enabled, visit `http://<host>:<port>/status` to fetch the latest status payload, including task timings and outcomes.

### Testing

The toolkit's standard library implementation means there are no runtime dependencies beyond Python itself.  For development,
install `pytest` and run the automated checks:

```
python -m pip install --upgrade pip pytest
python -m pytest -q
```

### Container usage

Because the toolkit has no external dependencies, containerising the agent is straightforward: copy the `infrastructure_agent/`
package and your configuration into an image built from a lightweight Python base, set the `INFRA_AGENT_VAULT_KEY`, and invoke
the CLI described above as the container's entrypoint.

Usage
-----
    class Article < ActiveRecord::Base
      acts_as_commentable
    end

* Add a comment to a model instance, for example an Article:

        @article = Article.find(params[:id])
        @user_who_commented = @current_user
        @comment = Comment.build_from( @article, @user_who_commented.id, "Hey guys this is my comment!" )

* To make a newly created comment into a child/reply of another comment:

        @comment.move_to_child_of(the_desired_parent_comment)

* To retrieve all comments for an article, including child comments:

        @all_comments = @article.comment_threads

* To retrieve only the root comments without their child comments:

        @root_comments = @article.root_comments

* To check if a comment has children:

        @comment.has_children?

* To verify the number of children a comment has:

        @comment.children.size

* To retrieve a comment's children:

        @comment.children

* If you plan to use the `acts_as_votable` plugin with your comment system be
  sure to uncomment the line [`acts_as_votable`][L9] in `lib/comment.rb`.

[L9]: https://github.com/elight/acts_as_commentable_with_threading/blob/master/lib/generators/acts_as_commentable_with_threading_migration/templates/comment.rb#L9

Credits
-------
* [xxx](https://github.com/xxx) - For contributing the updates for Rails 3!
* [Jack Dempsey](https://github.com/jackdempsey) - This plugin/gem is heavily
  influenced/liberally borrowed/stolen from [acts_as_commentable].

And in turn...

* Xelipe - Because acts_as_commentable was heavily influenced by Acts As Taggable.

[acts_as_commentable]: https://github.com/jackdempsey/acts_as_commentable

More
----
* [http://tripledogdare.net](http://tripledogdare.net)
* [http://evan.tiggerpalace.com](http://evan.tiggerpalace.com)
