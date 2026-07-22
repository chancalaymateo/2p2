"""Version del paquete (fuente unica de verdad).

La CI sobreescribe este archivo en cada build para inyectar la version real
(p.ej. 0.1.<numero_de_build>), de modo que la app 'sabe' su propia version y
puede compararla contra la ultima publicada en GitHub.
"""

__version__ = "0.1.0"
