import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from django.utils import timezone

# Importa o model Vaga (e tenta importar Permanencia caso já exista no models.py)
from .models import Vaga
try:
    from .models import Permanencia
except ImportError:
    Permanencia = None


# DM-19: Função vaga

def vaga_to_dict(vaga):
    """Converte o objeto Vaga para dicionário compatível com o JSON do front-end."""
    status_atual = str(vaga.status).strip().upper()
    return {
        "id": vaga.id,
        "numero": vaga.numero,
        "tipo": vaga.tipo,
        "status": status_atual,
        "ocupada": status_atual in ["OCUPADA", "OCUPADO", "TRUE"]
    }


# DM-20: Validação de número e tipo da vaga

TIPOS_PERMITIDOS = {"CARRO", "MOTO", "CAMINHAO", "CAMINHÃO", "UTILITARIO", "UTILITÁRIO", "PCD", "IDOSO"}
STATUS_PERMITIDOS = {"LIVRE", "OCUPADA", "DISPONIVEL", "DISPONÍVEL", "MANUTENCAO", "MANUTENÇÃO"}

def validar_vaga(data, vaga_id=None):
    numero = data.get("numero")
    tipo = data.get("tipo")
    status_vaga = data.get("status", "LIVRE")

    # Valida o número 
    if numero is None or str(numero).strip() == "":
        return "O número da vaga é obrigatório."
    
    numero_limpo = str(numero).strip()
    if numero_limpo.lstrip('-').isdigit() and int(numero_limpo) <= 0:
        return "O número da vaga deve ser maior que zero."

    # Verifica se existe outra vaga com o mesmo 
    duplicada = Vaga.objects.filter(numero__iexact=numero_limpo)
    if vaga_id is not None:
        duplicada = duplicada.exclude(id=vaga_id)
    if duplicada.exists():
        return f"Já existe uma vaga cadastrada com o número '{numero_limpo}'."

    # Valida o tipo da vaga
    if not tipo or str(tipo).strip() == "":
        return "O tipo da vaga é obrigatório."
    
    tipo_limpo = str(tipo).strip().upper()
    if tipo_limpo not in TIPOS_PERMITIDOS:
        return f"Tipo de vaga inválido ('{tipo}'). Valores aceitos: CARRO, MOTO, CAMINHAO, UTILITARIO."

    # Valida status da vaga
    if status_vaga:
        status_limpo = str(status_vaga).strip().upper()
        if status_limpo not in STATUS_PERMITIDOS:
            return f"Status inválido ('{status_vaga}'). Use LIVRE ou OCUPADA."

    return None



# DM-19 e DM-20: CRUD de Vagas + Filtro por Status

@csrf_exempt
def vagas_list_create(request):
    """
    GET  /api/vagas -> Lista todas as vagas ou filtra por ?status=LIVRE|OCUPADA (DM-20)
    POST /api/vagas -> Cria uma nova vaga com validação (DM-19 e DM-20)
    """
    if request.method == "GET":
        status_param = request.GET.get("status")
        vagas = Vaga.objects.all().order_by("id")

        if status_param:
            st = status_param.strip().upper()
            if st in ["LIVRE", "DISPONIVEL", "DISPONÍVEL", "FALSE"]:
                vagas = vagas.filter(status__iexact="LIVRE")
            elif st in ["OCUPADA", "OCUPADO", "TRUE"]:
                vagas = vagas.filter(status__iexact="OCUPADA")
            else:
                vagas = vagas.filter(status__iexact=st)

        return JsonResponse([vaga_to_dict(v) for v in vagas], safe=False, status=200)

    elif request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido."}, status=400)

        erro = validar_vaga(data)
        if erro:
            return JsonResponse({"erro": erro}, status=400)

        status_inicial = str(data.get("status", "LIVRE")).strip().upper()
        if status_inicial in ["DISPONIVEL", "DISPONÍVEL"]:
            status_inicial = "LIVRE"

        vaga = Vaga.objects.create(
            numero=str(data.get("numero")).strip(),
            tipo=str(data.get("tipo")).strip().upper(),
            status=status_inicial
        )
        return JsonResponse(vaga_to_dict(vaga), status=201)

    return JsonResponse({"erro": "Método não permitido."}, status=405)


@csrf_exempt
def vaga_detail(request, vaga_id):
    """
    GET    /api/vagas/<id> -> Detalha uma vaga específica
    PUT    /api/vagas/<id> -> Atualiza número, tipo ou status da vaga
    DELETE /api/vagas/<id> -> Exclui uma vaga (se não estiver ocupada)
    """
    try:
        vaga = Vaga.objects.get(id=vaga_id)
    except Vaga.DoesNotExist:
        return JsonResponse({"erro": "Vaga não encontrada."}, status=404)

    if request.method == "GET":
        return JsonResponse(vaga_to_dict(vaga), status=200)

    elif request.method in ["PUT", "PATCH"]:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido."}, status=400)

        dados_atualizados = {
            "numero": data.get("numero", vaga.numero),
            "tipo": data.get("tipo", vaga.tipo),
            "status": data.get("status", vaga.status),
        }

        erro = validar_vaga(dados_atualizados, vaga_id=vaga.id)
        if erro:
            return JsonResponse({"erro": erro}, status=400)

        novo_status = str(dados_atualizados["status"]).strip().upper()
        if novo_status in ["DISPONIVEL", "DISPONÍVEL"]:
            novo_status = "LIVRE"

        vaga.numero = str(dados_atualizados["numero"]).strip()
        vaga.tipo = str(dados_atualizados["tipo"]).strip().upper()
        vaga.status = novo_status
        vaga.save()

        return JsonResponse(vaga_to_dict(vaga), status=200)

    elif request.method == "DELETE":
        if str(vaga.status).strip().upper() == "OCUPADA":
            return JsonResponse({"erro": "Não é possível remover uma vaga ocupada."}, status=400)
        vaga.delete()
        return JsonResponse({"mensagem": "Vaga excluída com sucesso."}, status=200)

    return JsonResponse({"erro": "Método não permitido."}, status=405)



# DM-21: Implementar os quatro indicadores do dashboard

def dashboard_indicadores(request):
    """
    GET /api/dashboard -> Calcula e retorna os 4 indicadores principais do sistema.
    """
    if request.method != "GET":
        return JsonResponse({"erro": "Método não permitido."}, status=405)

    # indicador
    # Total de Vagas
    total_vagas = Vaga.objects.count()

    # Vagas Ocupadas
    vagas_ocupadas = Vaga.objects.filter(status__iexact="OCUPADA").count()

    # Vagas Livres
    vagas_livres = total_vagas - vagas_ocupadas

    # TAXA
    faturamento_hoje = 0.0
    faturamento_total = 0.0
    veiculos_ativos = vagas_ocupadas

    if Permanencia is not None:
        try:
            hoje = timezone.now().date()
            # Conta veículos estacionados no momento (sem data de saída)
            if hasattr(Permanencia, "data_saida"):
                veiculos_ativos = Permanencia.objects.filter(data_saida__isnull=True).count()
            elif hasattr(Permanencia, "saida"):
                veiculos_ativos = Permanencia.objects.filter(saida__isnull=True).count()

            # Soma valores das permanências finalizadas
            campo_valor = None
            for candidato in ["valor_total", "valor", "preco", "total"]:
                if hasattr(Permanencia, candidato):
                    campo_valor = candidato
                    break

            if campo_valor:
                soma_geral = Permanencia.objects.aggregate(total=Sum(campo_valor))["total"]
                faturamento_total = float(soma_geral or 0.0)

                if hasattr(Permanencia, "data_saida"):
                    soma_dia = Permanencia.objects.filter(data_saida__date=hoje).aggregate(total=Sum(campo_valor))["total"]
                    faturamento_hoje = float(soma_dia or 0.0)
                elif hasattr(Permanencia, "saida"):
                    soma_dia = Permanencia.objects.filter(saida__date=hoje).aggregate(total=Sum(campo_valor))["total"]
                    faturamento_hoje = float(soma_dia or 0.0)
                else:
                    faturamento_hoje = faturamento_total
        except Exception:
            pass

    taxa_ocupacao = round((vagas_ocupadas / total_vagas) * 100, 2) if total_vagas > 0 else 0.0

    # Retorna tanto em camelCase (padrão antigo do Java) quanto em snake_case (padrão Python)
    # para garantir compatibilidade imediata com o front-end (DM-22)
    return JsonResponse({
        "totalVagas": total_vagas,
        "vagasLivres": vagas_livres,
        "vagasDisponiveis": vagas_livres,
        "vagasOcupadas": vagas_ocupadas,
        "veiculosEstacionados": veiculos_ativos,
        "faturamentoHoje": round(faturamento_hoje, 2),
        "faturamentoTotal": round(faturamento_total, 2),
        "taxaOcupacao": taxa_ocupacao,
        "total_vagas": total_vagas,
        "vagas_livres": vagas_livres,
        "vagas_disponiveis": vagas_livres,
        "vagas_ocupadas": vagas_ocupadas,
        "veiculos_estacionados": veiculos_ativos,
        "faturamento_hoje": round(faturamento_hoje, 2),
        "faturamento_total": round(faturamento_total, 2),
        "taxa_ocupacao": taxa_ocupacao,
    }, status=200)