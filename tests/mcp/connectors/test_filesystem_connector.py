"""
Pruebas unitarias para FilesystemConnector.

Este módulo contiene pruebas que verifican el funcionamiento correcto
del conector de sistema de archivos para MCP.
"""

import os
import tempfile
import shutil
import unittest
from pathlib import Path

# Importar el componente a probar
from mcp.connectors.filesystem import FilesystemConnector

class TestFilesystemConnector(unittest.TestCase):
    """Pruebas para FilesystemConnector."""
    
    def setUp(self):
        """Configurar entorno de prueba."""
        # Crear directorio temporal para las pruebas
        self.test_dir = tempfile.mkdtemp()
        
        # Crear conector para pruebas
        self.connector = FilesystemConnector(
            root_path=self.test_dir,
            allow_write=True,
            max_file_size=1024 * 1024  # 1 MB
        )
        
        # Crear algunos archivos y directorios de prueba
        self.setup_test_files()
        
    def tearDown(self):
        """Limpiar después de las pruebas."""
        # Eliminar directorio temporal
        shutil.rmtree(self.test_dir)
        
    def setup_test_files(self):
        """Crear archivos y directorios de prueba."""
        # Crear un directorio
        os.makedirs(os.path.join(self.test_dir, "test_dir"))
        
        # Crear algunos archivos
        with open(os.path.join(self.test_dir, "test1.txt"), "w") as f:
            f.write("Contenido de prueba 1")
            
        with open(os.path.join(self.test_dir, "test2.txt"), "w") as f:
            f.write("Contenido de prueba 2")
            
        # Crear un archivo dentro del directorio
        with open(os.path.join(self.test_dir, "test_dir", "nested.txt"), "w") as f:
            f.write("Archivo anidado")
            
    def test_get_file_info(self):
        """Probar obtención de información de archivos."""
        # Obtener info de un archivo
        info = self.connector.get_file_info("/test1.txt")
        
        # Verificar datos básicos
        self.assertEqual(info["name"], "test1.txt")
        self.assertEqual(info["type"], "file")
        self.assertEqual(info["is_file"], True)
        self.assertEqual(info["is_dir"], False)
        self.assertEqual(info["extension"], "txt")
        
        # Obtener info de un directorio
        dir_info = self.connector.get_file_info("/test_dir")
        
        # Verificar datos del directorio
        self.assertEqual(dir_info["name"], "test_dir")
        self.assertEqual(dir_info["type"], "directory")
        self.assertEqual(dir_info["is_file"], False)
        self.assertEqual(dir_info["is_dir"], True)
        
    def test_list_directory(self):
        """Probar listado de directorios."""
        # Listar directorio raíz
        items = self.connector.list_directory("/")
        
        # Verificar que encuentra los archivos y directorios creados
        self.assertEqual(len(items), 3)  # test1.txt, test2.txt, test_dir
        
        # Verificar que hay dos archivos y un directorio
        files = [item for item in items if item["is_file"]]
        dirs = [item for item in items if item["is_dir"]]
        self.assertEqual(len(files), 2)
        self.assertEqual(len(dirs), 1)
        
        # Listar subdirectorio
        subitems = self.connector.list_directory("/test_dir")
        self.assertEqual(len(subitems), 1)  # nested.txt
        self.assertEqual(subitems[0]["name"], "nested.txt")
        
    def test_read_file(self):
        """Probar lectura de archivos."""
        # Leer un archivo
        content, info = self.connector.read_file("/test1.txt")
        
        # Verificar contenido
        self.assertEqual(content.decode("utf-8"), "Contenido de prueba 1")
        self.assertEqual(info["name"], "test1.txt")
        
        # Probar lectura de archivo anidado
        nested_content, _ = self.connector.read_file("/test_dir/nested.txt")
        self.assertEqual(nested_content.decode("utf-8"), "Archivo anidado")
        
        # Verificar error por archivo no existente
        with self.assertRaises(FileNotFoundError):
            self.connector.read_file("/no_existe.txt")
            
        # Verificar error por intentar leer un directorio
        with self.assertRaises(IsADirectoryError):
            self.connector.read_file("/test_dir")
            
    def test_write_file(self):
        """Probar escritura de archivos."""
        # Escribir un nuevo archivo
        info = self.connector.write_file("/nuevo.txt", "Contenido nuevo")
        
        # Verificar que se creó
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "nuevo.txt")))
        self.assertEqual(info["name"], "nuevo.txt")
        
        # Leer el contenido para verificar
        with open(os.path.join(self.test_dir, "nuevo.txt"), "r") as f:
            content = f.read()
        self.assertEqual(content, "Contenido nuevo")
        
        # Escribir en un directorio anidado que no existe
        self.connector.write_file("/nuevo_dir/anidado.txt", "Contenido anidado")
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "nuevo_dir", "anidado.txt")))
        
        # Sobrescribir un archivo existente
        self.connector.write_file("/test1.txt", "Contenido actualizado")
        with open(os.path.join(self.test_dir, "test1.txt"), "r") as f:
            updated_content = f.read()
        self.assertEqual(updated_content, "Contenido actualizado")
        
    def test_delete_item(self):
        """Probar eliminación de archivos y directorios."""
        # Eliminar un archivo
        self.connector.delete_item("/test1.txt")
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "test1.txt")))
        
        # Intentar eliminar un directorio no vacío sin recursión
        with self.assertRaises(IsADirectoryError):
            self.connector.delete_item("/test_dir")
            
        # Eliminar un directorio con recursión
        self.connector.delete_item("/test_dir", recursive=True)
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "test_dir")))
        
        # Verificar error por archivo no existente
        with self.assertRaises(FileNotFoundError):
            self.connector.delete_item("/no_existe.txt")
            
    def test_search_files(self):
        """Probar búsqueda de archivos."""
        # Buscar archivos .txt
        results = self.connector.search_files("/", "*.txt")
        
        # Verificar que encuentra todos los .txt
        self.assertEqual(len(results), 3)  # test1.txt, test2.txt, test_dir/nested.txt
        
        # Buscar archivos que empiezan con "test"
        results = self.connector.search_files("/", "test*.txt")
        self.assertEqual(len(results), 2)  # test1.txt, test2.txt
        
        # Buscar en un subdirectorio
        results = self.connector.search_files("/test_dir", "*.txt")
        self.assertEqual(len(results), 1)  # nested.txt
        
    def test_resolve_path(self):
        """Probar resolución de rutas."""
        # Resolver ruta normal
        path = self.connector._resolve_path("/test1.txt")
        expected = os.path.join(self.test_dir, "test1.txt")
        self.assertEqual(path, expected)
        
        # Nota: En Windows, el comportamiento de path normalization es diferente
        # y puede que no lance ValueError para rutas con ".." dependiendo de la
        # implementación. Verificamos el comportamiento real en lugar de asumir.
        try:
            path = self.connector._resolve_path("/../outside.txt")
            # Si no lanzó error, verificamos que la ruta esté dentro del directorio raíz
            self.assertTrue(path.startswith(self.test_dir),
                           f"La ruta {path} debería estar dentro de {self.test_dir}")
        except ValueError:
            # Si lanzó ValueError, es el comportamiento esperado en algunos sistemas
            pass
            
        # Intentar una ruta absoluta fuera del directorio
        absolute_path = os.path.abspath("/tmp/outside.txt")
        if not absolute_path.startswith(self.test_dir):
            try:
                path = self.connector._resolve_path(absolute_path)
                # Si no lanzó error, verificamos que la ruta esté dentro del directorio raíz
                self.assertTrue(path.startswith(self.test_dir),
                              f"La ruta {path} debería estar dentro de {self.test_dir}")
            except ValueError:
                # Si lanzó ValueError, es el comportamiento esperado
                pass
        
    def test_write_permissions(self):
        """Probar restricciones de escritura."""
        # Crear conector sin permisos de escritura
        read_only = FilesystemConnector(
            root_path=self.test_dir,
            allow_write=False
        )
        
        # Intentar escribir (debe fallar)
        with self.assertRaises(PermissionError):
            read_only.write_file("/test_write.txt", "No debería escribirse")
            
        # Verificar que no se creó el archivo
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "test_write.txt")))
        
        # Intentar eliminar (debe fallar)
        with self.assertRaises(PermissionError):
            read_only.delete_item("/test1.txt")
            
        # Verificar que el archivo sigue existiendo
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "test1.txt")))
        
if __name__ == "__main__":
    unittest.main() 