Labels. Choose exactly one:

- bug: something that should work does not. The file is the file whose code is wrong.
- feature: a request for new behaviour. The file is the file where the change would mainly go.
- question: the reporter asks how something works and nothing needs to change. The file is none.
- docs: the documentation is wrong or missing. The file is the document to fix.

A reporter who asks a question because a document told them something wrong has found a docs issue, not a question.
The file is where the cause is, which is not always where the reporter saw the symptom.
A label says what kind of issue it is, not which folder the file is in.
File paths are relative to the repository root, written exactly as the repository shows them (for example src/widgets/Frobnicator.tsx); never add or change a folder.
