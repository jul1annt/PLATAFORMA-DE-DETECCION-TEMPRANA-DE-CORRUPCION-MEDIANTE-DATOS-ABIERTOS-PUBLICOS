"""Standard-library entrypoint for the published inference environment probe."""
import json
from pathlib import Path
import sys


def main():
    backend = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend))
    from analytics_ml import inference
    from analytics_ml.runtime import prediction_code_sha256
    if not Path(inference.__file__).resolve().is_relative_to(backend):
        raise ValueError('La inferencia no pertenece al paquete seleccionado')
    print(json.dumps({
        'prefix': str(Path(sys.prefix).resolve()),
        'base_prefix': str(Path(sys.base_prefix).resolve()),
        'isolated': sys.flags.isolated,
        'prediction_code_sha256': prediction_code_sha256(),
        'training_dependencies_loaded': any(
            name.split('.')[0] in {'sklearn', 'numpy', 'scipy', 'joblib', 'threadpoolctl'}
            for name in sys.modules
        ),
    }))


if __name__ == '__main__':
    main()
