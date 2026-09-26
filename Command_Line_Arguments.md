# `khronos_d.py` Command-Line Arguments

`khronos_d.py` accepts the following command-line arguments:

```text
python khronos_d.py [options]
```

## Arguments

| Short form | Long form | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `-m` | `--query_size` | Integer | `9` | Number of servers queried for each offset calculation. |
| `-d` | `--filter_bounds` | Float | `0.334` | Fraction of sorted server offsets removed from each side before calculating the result. |
| `-k` | `--panic_threshold` | Integer | `5` | Maximum number of update failures before the client enters its panic condition. |
| `-w` | `--distance_threshold` | Float | `0.025` | Maximum permitted distance between offsets during the spread check. |
| `-e` | `--local_error_bound` | Float | `0.05` | Local error bound used when evaluating the calculated offset. |
| `-u` | `--update_query_interval` | Float | `60.0` seconds | Time between selecting a new set of servers. |
| `-q` | `--query_interval` | Float | `60.0` seconds | Time between offset queries. |
| `-p` | `--server_pool_path` | String | `khronos_servers_pool.json` | Path to the JSON file containing the server pool. |
| `-S` | `--state` | String | `current_s.json` | Path to the JSON file storing the last queried servers. |
| `-D` | `--dont_start_quick` | Flag | `false` | Do not start with a full update. This can cause a panic condition on the first update. |
| `-c` | `--conf_path` | String | `None` | Path to a JSON configuration file. When supplied, the file configuration is used instead of the other command-line parameter values. |
| `-C` | `--save_conf_path` | String | `config.json` | Path where the generated command-line configuration is saved as JSON. This is not the force-calibration flag. |
| `-o` | `--output_path` | String | `./` | Directory for generated output files. |
| `-n` | `--pool_size` | Integer | `9` | Number of servers to collect when calibrating the server pool. |
| `-Z` | `--zone_pools_path` | String | `zone_pools.json` | Path to the JSON file containing the DNS pools for each calibration zone. |
| `-z` | `--zone` | String | `global` | Calibration zone. Supported values are `global`, `europe`, `uk`, `usa`, `germany`, `singapore`, `australia`, `japan`, `asia`, and `south_america`. |
| `-f` | `--force_calibration` | Flag | `false` | Force calibration and regenerate the server pool file. |
| `-M` | `--max_calibration_time` | Integer | `7200` seconds | Maximum time allowed for server-pool calibration. |

The standard `-h`/`--help` option is also provided automatically by
`argparse`; it displays the command-line help and exits.

## Configuration-file behavior

When `--conf_path` is not supplied, command-line values are converted into
the configuration keys used by the client:

| Command-line option | Configuration key |
| --- | --- |
| `--query_size` | `total_servers_needed` |
| `--filter_bounds` | `fraction_to_use` |
| `--panic_threshold` | `max_tries` |
| `--distance_threshold` | `spread_limit` |
| `--local_error_bound` | `err` |
| `--update_query_interval` | `update_query_interval` |
| `--query_interval` | `query_interval` |
| `--server_pool_path` | `server_pool_path` |
| `--zone_pools_path` | `zone_pools_path` |
| `--state` | `state_path` |
| `--dont_start_quick` | `start_quick` (stored as the inverse value) |
| `--output_path` | `output_path` |
| `--zone` | `zone` |
| `--pool_size` | `pool_size` |
| `--max_calibration_time` | `max_calibration_time` |
| `--force_calibration` | `force_calibration` |

`--save_conf_path` controls where this generated configuration is written;
it is not included as a configuration key. If `--conf_path` is supplied,
the configuration is loaded from that file instead.

## Examples

Query 12 servers, use a 34% filter bound, and calibrate a UK pool:

```bash
python khronos_d.py \
  --query_size 12 \
  --filter_bounds 0.34 \
  --pool_size 500 \
  --max_calibration_time 36000 \
  --force_calibration \
  --zone uk \
  --server_pool_path khronos_servers_pool_london.json \
  --update_query_interval 3600 \
  --query_interval 60
```

Load an existing configuration file:

```bash
python khronos_d.py --conf_path config.json
```

## Additional Examples
```
python khronos_d.py -m 5 -d 0.2 -p khronos_servers_pool.json -S current_s.json
python khronos_d.py -m 5 -d 0.2 -p khronos_servers_pool.json -S current_s.json -w 0.025 -e 0.05 -o 
python khronos_d.py -m 5 -d 0.2 -p khronos_servers_pool_0.json -S current_s_0.json -w 0.025 -e 0.05 -o  -n 200 -M 300 -C -Z zone_pools.json
python khronos_d.py -m 12 -d 0.34  -w 0.025 -e 0.05 -n 500 -M 36000 -C -z usa -p khronos_servers_pool_oragon.json
python khronos_d.py -m 12 -d 0.34 -n 500 -M 36000 -C -z uk -p khronos_servers_pool_oragon.json -u 3600 -q 60
python khronos_d.py -m 12 -d 0.34 -z usa -p khronos_servers_pool_oragon.json -u 3600 -q 60
python khronos_d.py -m 12 -d 0.34 -n 500 -M 36000 -C -z germany -p khronos_servers_pool_frankfurt.json -u 3600 -q 60
python khronos_d.py -m 12 -d 0.34 -n 500 -M 36000 -C -z usa -p khronos_servers_pool_virginia.json -u 3600 -q 60
python khronos_d.py -m 12 -d 0.34 -n 500 -M 36000 -C -z uk -p khronos_servers_pool_london.json -u 3600 -q 60


```
