import importlib
import pkgutil

package_dir = __path__
package_name = __name__

for _, module_name, _ in pkgutil.iter_modules(package_dir):
    importlib.import_module(f'.{module_name}', package_name)
