# Email résumé preview

Turn a fictional application record and a plain-text résumé into a local email draft. The preview pairs the role and contact with a short work sample, then attaches the supplied résumé as `resume.txt`. Open the resulting `.eml` in a text editor to inspect its headers, message body and MIME attachment.

## Quickstart

Use Python 3.10 or later and its standard library. From the repository root, choose a fresh output filename on a local filesystem that supports hard links.

```sh
python3 preview.py examples/application.json examples/resume.txt --out application.eml
```

Expected terminal output

```text
To: Casey Example <casey@example.org>
Subject: Application for Map Index Assistant
Dry run saved to application.eml
```

The generated draft greets Casey, describes Alex’s practice map and includes the eight-street indexing exercise in the attached résumé. Each run requires a new output path so an earlier draft stays available for comparison.

## Try another application

Copy the JSON example and edit the applicant, contact, role, organization and work sample. The two mailbox fields accept simple addresses at `example.org`. Supply a UTF-8 plain-text résumé as the second argument. The command uses only the supplied files and the local output directory.

## Run the checks

```sh
python3 -m unittest discover -s tests -v
```

The checks run the command under a guard that stops Python socket, SMTP and process-launch operations. They parse the generated MIME message, compare the decoded attachment byte for byte with the supplied résumé, and check invalid records and existing output files.

## Provenance

The CLI, tests, application text and résumé were written for this standalone example. The applicant, contact, employer and work sample are fictional.
