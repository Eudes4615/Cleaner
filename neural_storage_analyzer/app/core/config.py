class Config:
    # Poids du score
    WEIGHT_SIZE = 0.25
    WEIGHT_AGE = 0.20
    WEIGHT_TYPE = 0.20
    WEIGHT_USAGE = 0.15
    WEIGHT_LOCATION = 0.20

    # Seuils
    MAX_SIZE_MB = 10000
    MAX_AGE_DAYS = 365

    # Taille minimale pour hashing
    HASH_MIN_SIZE_MB = 50
    HASH_QUICK_MAX_MB = 200

    # Extensions professionnelles supplémentaires
    EXTRA_EXTENSIONS = {
        'image': {'.heic', '.psd', '.ai', '.eps', '.raw', '.tga'},
        'video': {'.webm', '.m4a', '.mkv', '.mov'},
        '3d': {'.blend', '.dwg', '.dxf', '.step', '.stp', '.ifc', '.obj', '.stl'},
        'torrent': {'.torrent'},
    }