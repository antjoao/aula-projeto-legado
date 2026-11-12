from django.db import models

# =====================================================================
# (Mantenha aqui os models Cliente, Veiculo e Permanencia se já existirem)
# =====================================================================

class Vaga(models.Model):
    numero = models.CharField(max_length=20, unique=True)
    tipo = models.CharField(max_length=20)  # Ex: CARRO, MOTO, CAMINHAO
    status = models.CharField(max_length=20, default='LIVRE')  # Ex: LIVRE, OCUPADA

    class Meta:
        db_table = 'vagas'

    def __str__(self):
        return f"Vaga {self.numero} ({self.tipo}) - {self.status}"