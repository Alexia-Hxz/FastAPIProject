from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.models.base import Base
from app.schemas.common import ResponseModel

router = APIRouter(prefix="/codegen", tags=["代码生成器"])

PYTHON_TYPES = {
    "UUID": "str",
    "VARCHAR": "str",
    "TEXT": "str",
    "INTEGER": "int",
    "BIGINT": "int",
    "SMALLINT": "int",
    "BOOLEAN": "bool",
    "DATE": "str",
    "DATETIME": "str",
    "TIMESTAMP": "str",
    "FLOAT": "float",
    "DOUBLE": "float",
    "DECIMAL": "float",
    "JSON": "dict",
    "JSONB": "dict",
}


def _map_type(sql_type: str) -> str:
    sql_upper = sql_type.upper()
    for key, py_type in PYTHON_TYPES.items():
        if key in sql_upper:
            return py_type
    return "str"


def _generate_model_code(table_name: str, table) -> str:
    class_name = "".join(w.capitalize() for w in table_name.split("_"))
    lines = [f"class {class_name}(Base, UUIDMixin, TimestampMixin):"]
    lines.append(f'    __tablename__ = "{table_name}"')
    lines.append("")
    for col in table.columns:
        if col.name in ("id", "created_at", "updated_at"):
            continue
        py_type = _map_type(str(col.type))
        nullable = col.nullable
        default = col.default
        col_def = f"    {col.name}: Mapped[{py_type}"
        if nullable:
            col_def += f" | None"
        col_def += "] = mapped_column(...)"
        lines.append(col_def)
    return "\n".join(lines)


def _generate_schema_code(table_name: str, table) -> str:
    class_name = "".join(w.capitalize() for w in table_name.split("_"))
    lines = [f"class {class_name}Create(BaseModel):"]
    for col in table.columns:
        if col.name in ("id", "created_at", "updated_at"):
            continue
        py_type = _map_type(str(col.type))
        nullable = col.nullable
        if nullable:
            lines.append(f"    {col.name}: {py_type} | None = None")
        else:
            lines.append(f"    {col.name}: {py_type} = ...")
    lines.append("")
    lines.append(f"class {class_name}Update(BaseModel):")
    for col in table.columns:
        if col.name in ("id", "created_at", "updated_at"):
            continue
        py_type = _map_type(str(col.type))
        lines.append(f"    {col.name}: {py_type} | None = None")
    lines.append("")
    lines.append(f"class {class_name}Response(ORMBase):")
    for col in table.columns:
        py_type = _map_type(str(col.type))
        lines.append(f"    {col.name}: {py_type}")
    return "\n".join(lines)


@router.post("/generate")
async def generate_code(
    table_name: str = Query(..., description="Database table name"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("codegen:use")),
):
    table = Base.metadata.tables.get(table_name)
    if table is None:
        return ResponseModel(code=404, message=f"Table '{table_name}' not found", data=None)

    model_code = _generate_model_code(table_name, table)
    schema_code = _generate_schema_code(table_name, table)

    return ResponseModel(data={
        "table": table_name,
        "model": model_code,
        "schema": schema_code,
    })
