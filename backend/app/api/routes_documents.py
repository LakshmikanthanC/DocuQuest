from fastapi import BackgroundTasks
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.models.schemas import DocumentListResponse, DocumentPublic
from app.services import document_service
from app.services.document_service import DocumentRegistry, get_registry

router = APIRouter(prefix="/documents", tags=["documents"])


def _index_in_background(user_id: str, document_id: str) -> None:
    """Index a saved upload; failures are recorded on the record itself."""
    try:
        record = get_registry().get(user_id, document_id)
        if record is not None:
            document_service.index_document(record)
    except Exception:
        get_registry().update(document_id, status="failed")


@router.get("", response_model=DocumentListResponse)
def list_documents(
    current_user: dict = Depends(get_current_user),
    registry: DocumentRegistry = Depends(get_registry),
) -> DocumentListResponse:
    user_id = current_user["id"]
    records = registry.list_for_user(user_id)
    documents = [DocumentPublic.model_validate(r.public()) for r in records]
    return DocumentListResponse(documents=documents, total=len(documents))


@router.post("", response_model=DocumentPublic, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> DocumentPublic:
    user_id = current_user["id"]
    try:
        record = await document_service.save_upload(user_id, file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        await file.close()

    background_tasks.add_task(_index_in_background, user_id, record.id)
    return DocumentPublic.model_validate(record.public())


@router.get("/{document_id}", response_model=DocumentPublic)
def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    registry: DocumentRegistry = Depends(get_registry),
) -> DocumentPublic:
    record = registry.get(current_user["id"], document_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentPublic.model_validate(record.public())


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
) -> None:
    if not document_service.delete_document(current_user["id"], document_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
