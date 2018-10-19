ERROR_LIST = {
    1: (400, 'Missing parameter'),
    2: (400, 'Wrong parameter value'),
    3: (409, 'File already exists'),
    4: (400, 'Unsupported CRS of data file'),
    5: (400, 'Data file does not contain single layer'),
    6: (500, 'Cannot connect to database'),
    7: (500, 'Database query error'),
    8: (409, 'Reserved DB schema name'),
    9: (409, 'DB object already exists'),
    10: (409, 'DB schema owned by another than layman user'),
    11: (500, 'Error during import data into DB'),
    12: (409, 'GeoServer workspace not assigned to LAYMAN_GS_ROLE'),
    13: (409, 'Reserved GeoServer workspace name'),
    14: (400, 'Invalid SLD file'),
    15: (404, 'Layer was not found'),
    16: (404, 'Thumbnail was not found'),
    17: (409, 'Layer already exists'),
    18: (400, 'Missing one or more ShapeFile files.'),
    19: (400, 'Layer is already in process.'),
    20: (400, 'Chunk upload is not active for this layer.'),
    21: (400, 'Unknown combination of resumableFilename and '
              'layman_original_parameter.'),
    22: (400, 'MAX_INACTIVITY_TIME during upload reached.'),
}