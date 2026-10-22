"""Identity of the pure implementation shared by training and inference."""
import hashlib
from pathlib import Path


def prediction_code_sha256():
    package=Path(__file__).resolve().parent
    files={'analytics_ml/inference.py':package/'inference.py',
           'analytics_ml/runtime.py':package/'runtime.py',
           'modules/motor_riesgo/domain.py':package.parent/'modules/motor_riesgo/domain.py'}
    return {name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()}
