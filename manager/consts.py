from pathlib import Path


class Consts:

    # Default experiment values
    DEFAULT_REGION = "usa"
    DEFAULT_ATTACK_RATIO = 0.14

    DEFAULT_DELTA_NTP = 16
    DEFAULT_DELTA_CHRONOS = 10
    DEFAULT_TOTAL_TIME = 3600

    DEFAULT_SHIFT_TYPE = 'CONSTANT'
    DEFAULT_C_SHIFT = 0.2
    DEFAULT_SLOP_T_0 = 0
    DEFAULT_SLOP = 0.2

    DEFAULT_M = 12
    DEFAULT_D = 0.33
    DEFAULT_K = 3
    DEFAULT_W = 0.2
    DEFAULT_DRIFT = 0.2
    DEFAULT_SMOOTH = False

    # File paths
    zones_path = str(Path('resources', 'zones.txt').resolve())
    chronos_pool_path = str(Path('resources', 'chronos_test_pool.txt').resolve())
    calibration_pool_path = str(Path('resources', 'calibration_pool.txt').resolve())
    chronos_config_path = str(Path('resources', 'chronos_config.txt').resolve())
    chronos_truth_path = str(Path('resources', 'chronos_truth.txt').resolve())

    dns_files = [zones_path]
    chronos_files = [chronos_pool_path, chronos_config_path, chronos_truth_path]
