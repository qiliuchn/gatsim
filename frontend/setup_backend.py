import argparse
import json

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
    description="Configure GATSim backend"
    )
    parser.add_argument('--fork', type=str,   help='Fork name')
    parser.add_argument('--name', type=str,   help='Simulation name')
    parser.add_argument('--cmd',  type=str,   help='Command string')
    
    args = parser.parse_args()
    
    backend_args = {
        'fork': args.fork,
        'name': args.name,
        'cmd': args.cmd,
    }
    
    file_path = 'frontend/backend_args.json'
    with open(file_path, 'w') as f:
        json.dump(backend_args, f)
    