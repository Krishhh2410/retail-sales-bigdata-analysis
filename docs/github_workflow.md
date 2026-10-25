# GitHub workflow for three members (honest contribution history)
Rules: everyone commits their own work from their own account/machine; never fake authorship, backdate commits, or create filler commits.

## One-time setup (Member 1 = repo owner)
1. GitHub -> New repository `retail-sales-data-warehouse` (private is fine; no README).
2. Settings -> Collaborators -> add Member 2 and Member 3 (accept the email invitations).
3. Settings -> Branches -> protect `main`: require a pull request and 1 approval.
4. Member 1 pushes this project: 
```bash
git init && git add . && git commit -m "chore: initial project skeleton and agreed schema"
git branch -M main
git remote add origin https://github.com/<owner>/retail-sales-data-warehouse.git
git push -u origin main
```
5. Members 2 and 3: `git clone https://github.com/<owner>/retail-sales-data-warehouse.git && cd retail-sales-data-warehouse`
6. Each member sets their identity (must be their own): `git config user.name "Your Name"` and `git config user.email "<the email on your GitHub account>"`.

## Branches and ownership
```bash
git checkout -b feature/data-hdfs         # Member 1
git checkout -b feature/hive-warehouse    # Member 2
git checkout -b feature/spark-analytics   # Member 3
```
File ownership is in `docs/team_contributions.md`. Only edit another member's files through a pull request comment or a small, discussed commit.

## Suggested integration order
1. **Day 1 - schema freeze (Member 1):** merge `src/common.py`, `docs/data_dictionary.md`, a small sample CSV. This is the contract (column order, partition layout `region=/sales_year=/sales_month=`).
2. **Members 2 and 3 branch from updated `main`.** Member 2 builds DDL against the agreed layout; Member 3 builds Spark against `retail_dw.sales_partitioned` (use `--mode local-hive` until the cluster works).
3. Member 1 merges cleaning + partition tree + HDFS scripts. 4. Member 2 merges SQL + Hive workflow. 5. Member 3 merges Spark + charts + validator. 6. All three: integration test on the cluster, fix bugs via small PRs, then docs/report.

## Daily loop
```bash
git pull origin main --rebase          # get others' merged work
# ...edit your own files...
git add src/data/clean_data.py tests/test_data_quality.py
git commit -m "feat(data): implement retail data cleaning and HDFS ingestion"
git push -u origin feature/data-hdfs
```
Example commit messages (use many small real commits, not one big one):
* Member 1: `feat(data): add deterministic synthetic generator` - `feat(data): reject invalid quantities and duplicate ids` - `feat(hdfs): add upload and fsck verification scripts` - `test(data): add cleaning rule tests`
* Member 2: `feat(hive): create external staging and partitioned tables` - `feat(hive): register partitions with MSCK REPAIR` - `feat(hive): add top stores/products queries` - `feat(hive): add validation queries and workflow script`
* Member 3: `feat(spark): read Hive table with Hive support` - `feat(spark): revenue by category/region reports` - `feat(spark): monthly and seasonal analysis` - `feat(viz): add matplotlib charts` - `test(spark): compare Spark with pandas oracle`

## Pull requests and review
1. On GitHub: Compare & pull request -> base `main`, compare your branch; describe what, how tested, evidence.
2. Another member reviews (Files changed -> comment/suggest -> Approve). Rotate: M1 reviews M2, M2 reviews M3, M3 reviews M1.
3. Merge with "Squash and merge" **or** "Create a merge commit". Prefer *merge commit* or *rebase and merge* if you want each member's individual commits to stay visible; squash keeps one commit authored by the PR author.

## Merge conflicts
```bash
git checkout feature/hive-warehouse
git fetch origin && git merge origin/main      # or: git rebase origin/main
# conflict markers <<<<<<< ======= >>>>>>> appear in the file: edit to the correct final content together
git add <file> && git commit                   # (rebase: git rebase --continue)
git push
```
Most likely conflict: `docs/*.md` and `README.md` - agree who edits which section.

## Showing individual contributions
```bash
git log --oneline --all --graph
git shortlog -sn --all                       # commits per author
git log --author="Name" --stat --oneline     # files changed by a person
```
GitHub: Insights -> Contributors (commits/additions per person, computed from commits on the default branch); Pull requests -> Closed/Merged (review comments); each file's History/Blame. Take real screenshots near submission (see `docs/screenshots_checklist.md`).
