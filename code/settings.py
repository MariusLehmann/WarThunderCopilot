import os
from pathlib import Path

DEBUG_MODE = True

# keep legacy DB_PATH behaviour
PATH = Path(os.path.abspath(__file__)).parent
DB_PATH = os.path.join(PATH, 'settings.json')

WINDOW_UPDATE_INTERVALL = 100 # UpdateIntervall in ms
WINDOW_IDLE_UPDATE_INTERVALL = 1000 # Idle-UpdateIntervall in ms

# Logging defaults
# Use the project's paths module to determine the user/log directory
try:
	from paths import LOG_PATH as PATHS_LOG_DIR
except Exception:
	PATHS_LOG_DIR = PATH / 'logs'

LOG_DIR = PATHS_LOG_DIR
LOG_FILE = LOG_DIR / 'app.log'

# Primary minimum level for storing logs
LOG_LEVEL = 'DEBUG' if DEBUG_MODE else 'INFO'
# Messages at or above this level are additionally written to the central
# critical file (use string name like 'ERROR' or 'CRITICAL')
CRITICAL_LOG_LEVEL = 'ERROR'

LOGGING = {
	'version': 1,
	'disable_existing_loggers': False,
	'formatters': {
		'standard': {
			'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
		},
		'critical_prefixed': {
			'format': '%(asctime)s [%(name)s] - %(levelname)s - %(message)s'
		}
	},
	'handlers': {
		'console': {
			'class': 'logging.StreamHandler',
			'level': LOG_LEVEL,
			'formatter': 'standard',
			'stream': 'ext://sys.stdout'
		},
		'file': {
			'class': 'logging.handlers.RotatingFileHandler',
			'level': LOG_LEVEL,
			'formatter': 'standard',
			'filename': str(LOG_FILE),
			'mode': 'a',
			'maxBytes': 10 * 1024 * 1024,
			'backupCount': 5,
		},
		'critical_file': {
			'class': 'logging.handlers.RotatingFileHandler',
			'level': CRITICAL_LOG_LEVEL,
			'formatter': 'critical_prefixed',
			'filename': str(LOG_DIR / 'critical.log'),
			'mode': 'a',
			'maxBytes': 20 * 1024 * 1024,
			'backupCount': 10,
		}
	},
	'root': {
		'level': LOG_LEVEL,
		'handlers': ['console', 'file', 'critical_file']
	}
}


def configure_logging():
	"""Apply the central logging configuration.

	Creates the `LOG_DIR` if necessary and applies `LOGGING` via
	`logging.config.dictConfig`.
	"""
	import logging.config
	try:
		Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
	except Exception:
		# if we cannot create the directory, fall back to current working dir
		pass
	logging.config.dictConfig(LOGGING)