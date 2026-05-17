# Memory scale fixture

Synthetic dataset for **MEM-PERF-*** and **MEM-ACC-*** acceptance tests ([docs/17-acceptance-criteria.md](../../docs/17-acceptance-criteria.md) §7).

| Profile | Use | Characters | Diary segments | Mind loci / char | World loci / scene |
|---------|-----|------------|----------------|------------------|-------------------|
| `ci` | Default pytest | 24 | 1,200 | 40 | 20 |
| `reference` | Nightly / `pytest -m slow` | 24 | 12,000 | 200 | 100 |

## Seed programmatically

```python
from altrasia.fixtures.memory_scale import seed_memory_scale
from altrasia.persistence.sqlite_store import SqlitePersistence

store = SqlitePersistence("scale.db")
store.migrate()
meta = seed_memory_scale(store, profile="ci")
```

## Run perf tests

```bash
cd backend && python -m pytest ../tests/test_memory_perf.py -v
# full reference profile (slower):
cd backend && python -m pytest ../tests/test_memory_perf.py -v -m slow
```
