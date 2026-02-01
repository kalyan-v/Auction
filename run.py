import os
from app import create_app

# Get config from environment, default to development
config_name = os.environ.get('FLASK_CONFIG', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    debug = config_name == 'development'
    app.run(debug=debug, host='0.0.0.0', port=5000)
