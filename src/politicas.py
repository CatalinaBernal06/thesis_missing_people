"""Políticas de asignación de la Sección 5.1 de la tesis.

Cada política devuelve un vector de pesos de selección: 1 si el sitio se interviene y 0 si no.
La política sin información con costos homogéneos devuelve K/N para cada sitio, que es la
probabilidad de que un sitio sea elegido al azar; así, su valor esperado es exacto.
"""
import ctypes
import os
from contextlib import contextmanager

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

POLITICAS = ['Sin información', 'Menor costo', 'Mayor probabilidad de hallazgo',
             'Probabilidad de hallazgo por costo', 'Mochila']


@contextmanager
def silenciar_salida_c():
    """Silencia los mensajes que HiGHS (el solver de milp) escribe directamente en la salida estándar."""
    fd = os.dup(1)
    with open(os.devnull, 'w') as nulo:
        os.dup2(nulo.fileno(), 1)
        try:
            yield
        finally:
            ctypes.CDLL(None).fflush(None)  # vacía el búfer de C antes de restaurar la salida
            os.dup2(fd, 1)
            os.close(fd)


def codicioso(orden, c, B):
    a = np.zeros(len(c))
    restante = B
    for i in orden:
        if c[i] <= restante + 1e-9:
            a[i] = 1
            restante -= c[i]
    return a


def mochila(s, c, B):
    if c.min() > B:
        return np.zeros(len(c))
    if np.allclose(c, c[0]):  # costos homogéneos: los K de mayor puntaje (Lema 1)
        return codicioso(np.argsort(-s, kind='stable'), c, B)
    with silenciar_salida_c():
        res = milp(c=-s, constraints=LinearConstraint(c[None, :], -np.inf, B),
                   integrality=np.ones(len(s)), bounds=Bounds(0, 1))
    return np.round(res.x)


def politica(nombre, s, c, B):
    homogeneo = np.allclose(c, c[0])
    if nombre in ('Sin información', 'Menor costo'):
        if homogeneo:
            K = min(int(np.floor(B / c[0] + 1e-9)), len(c))
            return np.full(len(c), K / len(c))
        return codicioso(np.argsort(c, kind='stable'), c, B)
    if nombre == 'Mayor probabilidad de hallazgo':
        return codicioso(np.argsort(-s, kind='stable'), c, B)
    if nombre == 'Probabilidad de hallazgo por costo':
        return codicioso(np.argsort(-s / c, kind='stable'), c, B)
    if nombre == 'Mochila':
        return mochila(s, c, B)
    raise ValueError(nombre)


def seleccion(df, col_puntaje, nombre, col_costo, f):
    """Pesos de selección de una política en todos los municipios, con fracción f del presupuesto
    histórico de cada municipio (el costo de intervenir todos sus sitios)."""
    a = np.zeros(len(df))
    for _, idx in df.groupby('municipio').indices.items():
        c = df[col_costo].values[idx]
        a[idx] = politica(nombre, df[col_puntaje].values[idx], c, f * c.sum())
    return a
