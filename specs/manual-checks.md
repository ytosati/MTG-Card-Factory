# Card Factory — Manual checks

These checks cover the acceptance criteria marked "manual" in
[spec.md](spec.md). Each check runs on a Windows computer, follows numbered
steps and ends with an expected result and a result box to tick. The startup
and shutdown behavior they exercise is described in [plan.md](plan.md),
section 9.5.

The checks are grouped by milestone. Each milestone that adds a manual check
appends a new section at the end of this file and keeps the earlier checks
valid. A milestone review runs the checks of its milestone and records the
results in place; Milestone 10 runs the full list.

How to record a result:

- Tick **Passed** only when every step matched the expected result.
- Otherwise, leave the box empty and write what happened under **Notes**.
- Write the version from the `VERSION` file of the zip and the date of the run
  in the run record of the section.

## Prepare

What you need:

- A development machine with Windows, the repository, Python and Node, to
  build the zip.
- A test computer with Windows and **no Python and no Node installed**. It may
  be the same computer only for the milestones whose demo allows it
  (specs/tasks.md, "Delivery method"); Milestone 1 and Milestone 10 need a
  separate computer.
- A way to copy the zip to the test computer (USB drive or network share).
- For CA-20: a second device (computer or phone) on the same network as the
  test computer.

Steps:

1. On the development machine, commit or stash every change, so the tree is
   clean. The build stops when an included file differs from the last commit.
2. From the repository root, run:

   ```
   python release/build_release.py
   ```

   Expected: the output ends with a smoke test line of the form
   `django <version> | sqlite <version> | FTS5 ok`, followed by
   `Release zip ready: <repository>\release\build\card-factory-<version>-windows.zip`.
   Copy the smoke test line into "Build smoke test (FTS5)" below.
3. Copy `card-factory-<version>-windows.zip` to the test computer, for
   example to the Downloads folder.
4. On the test computer, open **Settings > Apps > Installed apps** and search
   for "Python" and for "Node". Expected: neither is installed.
5. Keep the zip as it is for CA-17 (first case). For the other checks, extract
   it: right-click the zip, choose **Extract All**, and extract it to a folder
   you own, such as Documents. Explorer names the extracted folder after the
   zip. In this file, "the Card Factory folder" means that extracted folder.
6. Open the Card Factory folder. Expected: it contains the folders `python`,
   `app` and `launcher`, and the files `Start Card Factory.cmd`, `.env`,
   `README.md` and `VERSION`.

If Windows shows a security warning when a file is opened, write it under
**Notes** of the check where it appeared.

## Build smoke test (FTS5)

The release build runs the zip's own `python.exe` after assembly: it imports
Django, Django REST Framework and waitress and creates an FTS5 table
(plan.md, section 9.5). Record its output for each build that a review uses.

| Version | Date | Smoke test line | Result |
|---|---|---|---|
| 0.1.0 | 2026-11-09 | `django 5.2.19 \| sqlite 3.49.1 \| FTS5 ok` | [x] FTS5 ok |

## Milestone 1 — Double-click start

Run record: version ______ · date ______ · Windows version ______

All checks in this section run from the locally built zip on the test computer
described in "Prepare".

### CA-45: Double-click start on a computer with no Python or Node

1. In the Card Factory folder, right-click `.env`, choose **Open with**, then
   **Notepad**.
2. Fill in `LLM_PROVIDER` (`openai`, `anthropic` or `google`), `LLM_API_KEY`
   and `LLM_MODEL`. Leave `APP_PORT=47821`. Startup never contacts a provider,
   so a placeholder key such as `sk-example-not-a-real-key` is enough for this
   check.
3. Save the file and close Notepad.
4. Double-click `Start Card Factory.cmd`.

Expected: a console window flashes for under a second and closes; no
terminal stays open and nothing is typed. The default browser opens
`http://127.0.0.1:47821/` and shows the **Status** screen. The value of
`LLM_API_KEY` appears nowhere on the screen.

- [ ] Passed

Notes:

### CA-20: Reachable only from this computer, no firewall prompt

1. Make sure Card Factory is not running: open **Task Manager**, tab
   **Details**, and check that no `pythonw.exe` is listed.
2. Double-click `Start Card Factory.cmd` and watch the screen until the
   Status screen opens.
3. Find the network address of the test computer: **Settings > Network &
   internet**, open the connection in use (Wi-Fi or Ethernet), then
   **Properties**; note the IPv4 address.
4. On the second device, on the same network, open a browser and go to
   `http://<IPv4 address>:47821/`.
5. On the test computer, open a new browser tab and go to
   `http://<IPv4 address>:47821/`.

Expected: at step 2, no Windows Security Alert or firewall window appears. At
steps 4 and 5, the page does not load (the browser reports that it cannot
connect). The tab on `http://127.0.0.1:47821/` keeps working.

- [ ] Passed

Notes:

### CA-47: Start, second start, reload and stop after the last tab

Start with Card Factory not running (no `pythonw.exe` in **Task Manager >
Details**).

**Start**

1. Double-click `Start Card Factory.cmd`.

Expected: the default browser opens a tab on `http://127.0.0.1:47821/` with
the Status screen.

- [ ] Passed

**Second start**

1. With the first tab still open, double-click `Start Card Factory.cmd`
   again.
2. Open **Task Manager > Details** after a few seconds.

Expected: a new tab opens on `http://127.0.0.1:47821/` with the Status screen.
Only one `pythonw.exe` remains listed.

- [ ] Passed

**Second start after a port change**

1. With Card Factory running, open `.env` in Notepad, set `APP_PORT=47822`
   and save.
2. Double-click `Start Card Factory.cmd`.
3. Open `.env` again, set `APP_PORT=47821` and save.

Expected: at step 2, a new tab opens on `http://127.0.0.1:47821/`, the port
of the running instance; no error window appears.

- [ ] Passed

**Reload and background tab**

1. In a Card Factory tab, press F5 several times over one minute.
2. Close every Card Factory tab but one. Switch to another tab or minimize
   the browser, and leave it for at least five minutes.
3. Return to the Card Factory tab.

Expected: the Status screen reloads each time. After step 3, the page works
and shows no "Card Factory has stopped." banner; `pythonw.exe` is still listed
in **Task Manager > Details**.

- [ ] Passed

**Stop after the last tab**

1. Close every Card Factory tab (or close the browser). Note the time.
2. Watch **Task Manager > Details**.

Expected: `pythonw.exe` disappears within four minutes of closing the last
tab.

- [ ] Passed

**Tab left open after the application stopped**

1. Double-click `Start Card Factory.cmd` and keep the tab that opens.
2. In **Task Manager > Details**, select `pythonw.exe` and choose **End
   task**.
3. Wait about 20 seconds and look at the tab.
4. Double-click `Start Card Factory.cmd` again, then return to the old tab
   and wait about 20 seconds.

Expected: at step 3, the old tab shows the banner "Card Factory has stopped."
with the text "To start it again, double-click the start file in its folder
and use the new tab it opens." At step 4, a new tab opens on the Status
screen, and the banner on the old tab disappears.

- [ ] Passed

Notes:

The part of CA-47 about the database build or a generation keeping the
application running is checked by the milestone that adds those jobs.

### CA-17: Startup problems show the problem and the fix

**Started from inside the zip**

1. In Explorer, double-click the zip (do not extract it) to browse its
   contents.
2. Double-click `Start Card Factory.cmd` inside it.

Expected: a console window stays open with "Card Factory cannot start from
here.", the folder where the file was looked for, and the fix: extract the
whole zip first (right-click the zip, then **Extract All**), open the
extracted folder and double-click `Start Card Factory.cmd` there. It closes
when a key is pressed.

- [ ] Passed

**Folder without write permission**

1. Make sure Card Factory is not running.
2. Right-click the Card Factory folder, choose **Properties > Security >
   Edit**, select your user name and tick **Deny** for **Write**. Apply.
3. Double-click `Start Card Factory.cmd`.
4. Undo step 2: untick **Deny** for **Write** and apply.

Expected: at step 3, a message box titled "Card Factory" says "Card Factory
cannot write to its folder:" with the folder path, and tells you to move the
Card Factory folder to a place where you can create files, such as your
Documents folder, and start it again from there. No browser tab opens.

- [ ] Passed

**Data folder that cannot be written**

1. Make sure Card Factory is not running.
2. In the Card Factory folder, rename the `data` folder to `data-saved`.
3. Create an empty file named `data` with no extension (in Explorer, turn on
   **View > Show > File name extensions** first).
4. Double-click `Start Card Factory.cmd`.
5. Delete the `data` file and rename `data-saved` back to `data`.

Expected: at step 4, a message box titled "Card Factory" says "Card Factory
cannot write to its data folder:" with the path, and tells you to make sure
the data folder is a folder you can write to (not read-only and not a file),
or to move the Card Factory folder to your Documents folder, and start it
again.

- [ ] Passed

**No configuration file**

1. Make sure Card Factory is not running.
2. Rename `.env` to `env-saved.txt`.
3. Double-click `Start Card Factory.cmd`.
4. Rename `env-saved.txt` back to `.env`.

Expected: at step 3, a message box titled "Card Factory" says "The
configuration file .env is missing:" with the path, and tells you to extract
the release zip again, or copy the `.env` file from it into the Card Factory
folder, then start Card Factory again.

- [ ] Passed

Notes:

### CA-53: Default port in use

**Port used by another program**

1. Make sure Card Factory is not running.
2. Open **Windows PowerShell** (this terminal only simulates another program
   holding the port) and run:

   ```
   $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 47821)
   $listener.Start()
   ```

3. Double-click `Start Card Factory.cmd`.
4. Open `.env`, set `APP_PORT=47822` and save.
5. Double-click `Start Card Factory.cmd`.
6. Close every Card Factory tab, run `$listener.Stop()` in PowerShell, close
   PowerShell, and set `APP_PORT=47821` in `.env` again.

Expected: at step 3, a message box titled "Card Factory" says "Card Factory
cannot use port 47821:" and that another program is using it (or may be using
it), and tells you to close the program that uses port 47821, or set
`APP_PORT` in `.env` to another port, then start Card Factory again. At step
5, the browser opens `http://127.0.0.1:47822/` with the Status screen.

- [ ] Passed

**Port used by a Card Factory from another folder**

1. Extract the same zip a second time, to another folder (for example
   Documents\Card Factory 2), and fill in its `.env` as in CA-45.
2. Start Card Factory from the first folder and keep its tab open.
3. Double-click `Start Card Factory.cmd` in the second folder.
4. In the second folder, set `APP_PORT=47822` in `.env` and save.
5. Double-click `Start Card Factory.cmd` in the second folder.
6. Close every Card Factory tab and let both stop.

Expected: at step 3, a message box titled "Card Factory" says "Card Factory
cannot use port 47821: another Card Factory, started from another folder, is
using it.", and tells you to close the other Card Factory, or set `APP_PORT`
in `.env` to another port, then start Card Factory again. At step 5, the
browser opens `http://127.0.0.1:47822/` with the Status screen of the second
folder, while the first one keeps running on port 47821.

- [ ] Passed

Notes:
