import os
import pymysql.cursors

# MySQL connection parameters
MYSQL_HOST = 'host'
MYSQL_USER = 'user'
MYSQL_PASSWORD = 'pass'
MYSQL_DB = 'db'


# Function to generate Sequelize model code
def generate_model_code(table_name, columns, foreign_keys, indexes):
    model_code = f"const Sequelize = require('sequelize');\n\n"
    model_code += f"module.exports = (sequelize) => {{\n"
    model_code += f"  const {table_name} = sequelize.define('{table_name}', {{\n"

    for column in columns:
        column_name = column['Field']
        data_type = column['Type']
        is_nullable = column['Null'] == 'YES'
        default_value = column['Default']

        # Convert MySQL data types to Sequelize data types
        data_type_map = {
            'int': 'Sequelize.INTEGER',
            'varchar': 'Sequelize.STRING',
            'text': 'Sequelize.TEXT',
            'datetime': 'Sequelize.DATE',
            # Add more data types here
        }

        sequelize_data_type = data_type_map.get(data_type.split('(')[0], 'Sequelize.STRING')

        # Add ' on string columns
        if 'CHAR' in data_type.upper() or 'TEXT' in data_type.upper():
            sequelize_data_type += "()"

        # Construct Sequelize column definition
        column_definition = f"    {column_name}: {{\n"
        column_definition += f"      type: {sequelize_data_type},\n"
        if not is_nullable:
            column_definition += f"      allowNull: false,\n"
        if default_value is not None:
            column_definition += f"      defaultValue: '{default_value}',\n"
        column_definition += "    },\n"

        model_code += column_definition

    model_code += "  }, {\n"
    model_code += f"    tableName: '{table_name}',\n"
    model_code += "    timestamps: false,\n"

    if foreign_keys:
        model_code += "    foreignKeys: [\n"
        for fk in foreign_keys:
            model_code += f"      {{\n"
            model_code += f"        name: '{fk['CONSTRAINT_NAME']}',\n"
            model_code += f"        fields: ['{fk['COLUMN_NAME']}'],\n"
            model_code += f"        references: {{\n"
            model_code += f"          model: '{fk['REFERENCED_TABLE_NAME']}',\n"
            model_code += f"          key: '{fk['REFERENCED_COLUMN_NAME']}'\n"
            model_code += f"        }}\n"
            model_code += f"      }},\n"
        model_code += "    ],\n"

    # Add indexes to model definition
    if indexes:
        model_code += "    indexes: [\n"
        for idx in indexes:
            index_name = idx['Key_name']
            if index_name != 'PRIMARY':
                unique = 'unique' if idx['Non_unique'] == 0 else ''
                fields = ', '.join([f"'{idx['Column_name']}'" for idx in indexes if idx['Key_name'] == index_name])
                model_code += f"      {{ name: '{index_name}', fields: [{fields}], type: '{unique}' }},\n"
        model_code += "    ],\n"

    model_code += "  });\n\n"

    # Add sequelize sync function
    model_code += f"  {table_name}.sync();\n"

    model_code += f"  return {table_name};\n}};"

    return model_code

# Output directory for generated model files
OUTPUT_DIR = 'models'

# Initialize MySQL connection
connection = pymysql.connect(host=MYSQL_HOST,
                             user=MYSQL_USER,
                             password=MYSQL_PASSWORD,
                             db=MYSQL_DB,
                             cursorclass=pymysql.cursors.DictCursor)

try:
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with connection.cursor() as cursor:
        # Get list of tables in the database
        cursor.execute('SHOW TABLES')
        tables = cursor.fetchall()

        for table in tables:
            table_name = table['Tables_in_' + MYSQL_DB]
            file_name = f"{table_name.lower()}.js"
            file_path = os.path.join(OUTPUT_DIR, file_name)

            # Fetch table columns
            cursor.execute(f"SHOW FULL COLUMNS FROM {table_name}")
            columns = cursor.fetchall()

            # Fetch foreign key constraints
            cursor.execute(f"SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = '{MYSQL_DB}' AND TABLE_NAME = '{table_name}' AND REFERENCED_TABLE_NAME IS NOT NULL")
            foreign_keys = cursor.fetchall()

            # Fetch indexes
            cursor.execute(f"SHOW INDEXES FROM {table_name}")
            indexes = cursor.fetchall()

            # Generate Sequelize model code
            model_code = generate_model_code(table_name, columns, foreign_keys, indexes)

            # Write model code to file
            with open(file_path, 'w') as f:
                f.write(model_code)

            print(f"Model file generated: {file_path}")

finally:
    connection.close()
