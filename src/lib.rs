use pyo3::exceptions::{PyException, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PySequence, PyString, PyTuple, PyType};
use pyo3::{Py, PyTypeInfo};

// ─── Exception hierarchy ────────────────────────────────────────

pyo3::create_exception!(bgm_tv_wiki, WikiSyntaxError, PyException);
pyo3::create_exception!(bgm_tv_wiki, GlobalPrefixError, WikiSyntaxError);
pyo3::create_exception!(bgm_tv_wiki, GlobalSuffixError, WikiSyntaxError);
pyo3::create_exception!(bgm_tv_wiki, ArrayNoCloseError, WikiSyntaxError);
pyo3::create_exception!(bgm_tv_wiki, InvalidArrayItemError, WikiSyntaxError);
pyo3::create_exception!(bgm_tv_wiki, ExpectingNewFieldError, WikiSyntaxError);
pyo3::create_exception!(bgm_tv_wiki, ExpectingSignEqualError, WikiSyntaxError);
pyo3::create_exception!(bgm_tv_wiki, DuplicatedKeyError, PyException);

// ─── Helper: raise WikiSyntaxError subclass with lino/line/message attrs ────

fn raise_syntax_err<T>(
    py: Python<'_>,
    exc_type: &Bound<'_, pyo3::PyAny>,
    lino: Option<usize>,
    line: Option<&str>,
    message: &str,
) -> PyResult<T> {
    let msg = if let Some(l) = lino {
        format!("{l}: {message}")
    } else {
        message.to_string()
    };
    let exc_type: Bound<'_, PyType> = exc_type.cast().unwrap().clone();
    let err = PyErr::from_type(exc_type, msg);
    let inst = err.value(py);
    inst.setattr("lino", lino)?;
    inst.setattr("line", line)?;
    inst.setattr("message", message)?;
    Err(err)
}

fn raise_global_prefix<T>(py: Python<'_>) -> PyResult<T> {
    raise_syntax_err(
        py,
        GlobalPrefixError::type_object(py).as_ref(),
        None,
        None,
        "missing prefix '{{Infobox' at the start",
    )
}

fn raise_global_suffix<T>(py: Python<'_>) -> PyResult<T> {
    raise_syntax_err(
        py,
        GlobalSuffixError::type_object(py).as_ref(),
        None,
        None,
        "missing '}}' at the end",
    )
}

fn raise_array_no_close<T>(py: Python<'_>, lino: Option<usize>, line: Option<&str>) -> PyResult<T> {
    raise_syntax_err(
        py,
        ArrayNoCloseError::type_object(py).as_ref(),
        lino,
        line,
        "array not close",
    )
}

fn raise_invalid_array_item<T>(
    py: Python<'_>,
    lino: Option<usize>,
    line: Option<&str>,
) -> PyResult<T> {
    raise_syntax_err(
        py,
        InvalidArrayItemError::type_object(py).as_ref(),
        lino,
        line,
        "invalid array item",
    )
}

fn raise_expecting_new_field<T>(
    py: Python<'_>,
    lino: Option<usize>,
    line: Option<&str>,
) -> PyResult<T> {
    raise_syntax_err(
        py,
        ExpectingNewFieldError::type_object(py).as_ref(),
        lino,
        line,
        "missing '|' at the beginning of line",
    )
}

fn raise_expecting_sign_equal<T>(
    py: Python<'_>,
    lino: Option<usize>,
    line: Option<&str>,
) -> PyResult<T> {
    raise_syntax_err(
        py,
        ExpectingSignEqualError::type_object(py).as_ref(),
        lino,
        line,
        "missing '=' in line",
    )
}

// ─── Item ───────────────────────────────────────────────────────

#[pyclass(frozen, eq, hash, from_py_object)]
#[derive(Clone, PartialEq, Eq, Hash)]
struct Item {
    #[pyo3(get)]
    key: String,
    #[pyo3(get)]
    value: String,
}

#[pymethods]
impl Item {
    #[new]
    #[pyo3(signature = (*, key="".to_string(), value="".to_string()))]
    fn new(key: String, value: String) -> Self {
        Item { key, value }
    }

    fn __repr__(&self) -> String {
        format!("Item(key={:?}, value={:?})", self.key, self.value)
    }
}

// ─── Value enum (Rust side) ─────────────────────────────────────

#[derive(Clone)]
enum FieldValue {
    None_,
    Str(String),
    Array(Vec<Item>),
}

impl FieldValue {
    fn to_py(&self, py: Python<'_>) -> Py<PyAny> {
        match self {
            FieldValue::None_ => py.None(),
            FieldValue::Str(s) => PyString::new(py, s).into_any().unbind(),
            FieldValue::Array(items) => {
                let py_items: Vec<Py<PyAny>> = items
                    .iter()
                    .map(|it| Py::new(py, it.clone()).unwrap().into_any())
                    .collect();
                PyTuple::new(py, &py_items).unwrap().into_any().unbind()
            }
        }
    }

    fn is_truthy(&self) -> bool {
        match self {
            FieldValue::None_ => false,
            FieldValue::Str(s) => !s.is_empty(),
            FieldValue::Array(v) => !v.is_empty(),
        }
    }

    fn emp_key(&self) -> i32 {
        match self {
            FieldValue::None_ => 1,
            FieldValue::Str(_) => 2,
            FieldValue::Array(_) => 3,
        }
    }

    fn from_py(obj: &Bound<'_, pyo3::PyAny>) -> PyResult<Self> {
        if obj.is_none() {
            return Ok(FieldValue::None_);
        }
        if let Ok(s) = obj.cast::<PyString>() {
            return Ok(FieldValue::Str(s.to_str()?.to_string()));
        }
        if let Ok(tup) = obj.cast::<PyTuple>() {
            let mut items = Vec::with_capacity(tup.len());
            for item in tup.iter() {
                let it: PyRef<'_, Item> = item.extract()?;
                items.push(it.clone());
            }
            return Ok(FieldValue::Array(items));
        }
        // Try sequence
        if let Ok(seq) = obj.cast::<PySequence>() {
            let mut items = Vec::with_capacity(seq.len()?);
            for i in 0..seq.len()? {
                let item = seq.get_item(i)?;
                let it: PyRef<'_, Item> = item.extract()?;
                items.push(it.clone());
            }
            return Ok(FieldValue::Array(items));
        }
        Err(PyTypeError::new_err("unsupported value type"))
    }
}

impl PartialEq for FieldValue {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (FieldValue::None_, FieldValue::None_) => true,
            (FieldValue::Str(a), FieldValue::Str(b)) => a == b,
            (FieldValue::Array(a), FieldValue::Array(b)) => a == b,
            _ => false,
        }
    }
}
impl Eq for FieldValue {}

// ─── Field ──────────────────────────────────────────────────────

#[pyclass(frozen, from_py_object)]
#[derive(Clone)]
struct Field {
    #[pyo3(get)]
    key: String,
    value_inner: FieldValue,
}

#[pymethods]
impl Field {
    #[new]
    #[pyo3(signature = (*, key, value=None))]
    fn new(key: String, value: Option<&Bound<'_, pyo3::PyAny>>) -> PyResult<Self> {
        let fv = match value {
            None => FieldValue::None_,
            Some(obj) => FieldValue::from_py(obj)?,
        };
        Ok(Field {
            key,
            value_inner: fv,
        })
    }

    #[getter]
    fn value(&self, py: Python<'_>) -> Py<PyAny> {
        self.value_inner.to_py(py)
    }

    fn __repr__(&self, py: Python<'_>) -> String {
        let val_repr = self.value_inner.to_py(py);
        format!(
            "Field(key={:?}, value={})",
            self.key,
            val_repr
                .bind(py)
                .repr()
                .map(|r: Bound<'_, PyString>| r.to_string())
                .unwrap_or_else(|_| "?".to_string())
        )
    }

    fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {
        let val = self.value_inner.to_py(py);
        let key_obj: Py<PyAny> = PyString::new(py, &self.key).into_any().unbind();
        let tup = PyTuple::new(py, &[key_obj, val])?;
        tup.hash()
    }

    fn __eq__(&self, other: &Bound<'_, pyo3::PyAny>) -> bool {
        if let Ok(o) = other.extract::<PyRef<'_, Field>>() {
            self.key == o.key && self.value_inner == o.value_inner
        } else {
            false
        }
    }

    fn __ne__(&self, other: &Bound<'_, pyo3::PyAny>) -> bool {
        if let Ok(o) = other.extract::<PyRef<'_, Field>>() {
            self.key != o.key || self.value_inner != o.value_inner
        } else {
            true
        }
    }

    fn __lt__(&self, other: &Field) -> bool {
        if self.key != other.key {
            return self.key < other.key;
        }
        self.value_inner.emp_key() < other.value_inner.emp_key()
    }

    fn semantically_equal(&self, other: &Field) -> bool {
        if self.key != other.key {
            return false;
        }
        match (&self.value_inner, &other.value_inner) {
            (FieldValue::Array(_), _) | (_, FieldValue::Array(_)) => {
                self.value_inner == other.value_inner
            }
            _ => {
                if !self.value_inner.is_truthy() && !other.value_inner.is_truthy() {
                    true
                } else {
                    self.value_inner == other.value_inner
                }
            }
        }
    }
}

// ─── Wiki ───────────────────────────────────────────────────────

#[pyclass(frozen, from_py_object)]
#[derive(Clone)]
struct Wiki {
    #[pyo3(get)]
    r#type: Option<String>,
    fields_inner: Vec<Field>,
    #[pyo3(get)]
    _eol: String,
}

impl Wiki {
    fn make(type_: Option<String>, fields: Vec<Field>, eol: String) -> Self {
        Wiki {
            r#type: type_,
            fields_inner: fields,
            _eol: eol,
        }
    }
}

#[pymethods]
impl Wiki {
    #[new]
    #[pyo3(signature = (*, r#type=None, fields=None, _eol="\n".to_string()))]
    fn new(
        r#type: Option<String>,
        fields: Option<&Bound<'_, PyTuple>>,
        _eol: String,
    ) -> PyResult<Self> {
        let flds = match fields {
            None => Vec::new(),
            Some(tup) => {
                let mut v = Vec::with_capacity(tup.len());
                for item in tup.iter() {
                    v.push(item.extract::<Field>()?);
                }
                v
            }
        };
        Ok(Wiki::make(r#type, flds, _eol))
    }

    #[getter]
    fn fields(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let items: Vec<Py<PyAny>> = self
            .fields_inner
            .iter()
            .map(|f| Py::new(py, f.clone()).unwrap().into_any())
            .collect();
        Ok(PyTuple::new(py, &items)?.into_any().unbind())
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let fields_obj = self.fields(py)?;
        let fields_repr = fields_obj.bind(py).repr()?;
        Ok(format!(
            "Wiki(type={:?}, fields={}, _eol={:?})",
            self.r#type, fields_repr, self._eol
        ))
    }

    fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {
        let type_obj: Py<PyAny> = match &self.r#type {
            Some(s) => PyString::new(py, s).into_any().unbind(),
            None => py.None(),
        };
        let fields_obj = self.fields(py)?;
        let eol_obj: Py<PyAny> = PyString::new(py, &self._eol).into_any().unbind();
        let tup = PyTuple::new(py, &[type_obj, fields_obj, eol_obj])?;
        tup.hash()
    }

    fn __eq__(&self, other: &Bound<'_, pyo3::PyAny>) -> bool {
        if let Ok(o) = other.extract::<PyRef<'_, Wiki>>() {
            self.r#type == o.r#type && self.fields_inner == o.fields_inner && self._eol == o._eol
        } else {
            false
        }
    }

    fn __ne__(&self, other: &Bound<'_, pyo3::PyAny>) -> bool {
        if let Ok(o) = other.extract::<PyRef<'_, Wiki>>() {
            self.r#type != o.r#type || self.fields_inner != o.fields_inner || self._eol != o._eol
        } else {
            true
        }
    }

    fn __str__(&self) -> String {
        render_impl(self)
    }

    fn keys(&self) -> Vec<String> {
        self.fields_inner.iter().map(|f| f.key.clone()).collect()
    }

    fn field_keys(&self) -> Vec<String> {
        self.keys()
    }

    fn non_zero(&self) -> Self {
        let mut result = Vec::new();
        for f in &self.fields_inner {
            match &f.value_inner {
                FieldValue::None_ => continue,
                FieldValue::Str(s) => {
                    if !s.is_empty() {
                        result.push(f.clone());
                    }
                }
                FieldValue::Array(items) => {
                    let filtered: Vec<Item> = items
                        .iter()
                        .filter(|it| !it.key.is_empty() || !it.value.is_empty())
                        .cloned()
                        .collect();
                    if !filtered.is_empty() {
                        result.push(Field {
                            key: f.key.clone(),
                            value_inner: FieldValue::Array(filtered),
                        });
                    }
                }
            }
        }
        Wiki::make(self.r#type.clone(), result, self._eol.clone())
    }

    fn get(&self, py: Python<'_>, key: &str) -> Py<PyAny> {
        for f in &self.fields_inner {
            if f.key == key {
                return f.value_inner.to_py(py);
            }
        }
        py.None()
    }

    fn get_all(&self, key: &str) -> Vec<String> {
        for f in &self.fields_inner {
            if f.key == key {
                match &f.value_inner {
                    FieldValue::None_ => return Vec::new(),
                    FieldValue::Str(s) => {
                        if s.is_empty() {
                            return Vec::new();
                        }
                        return vec![s.clone()];
                    }
                    FieldValue::Array(items) => {
                        return items.iter().map(|it| it.value.clone()).collect();
                    }
                }
            }
        }
        Vec::new()
    }

    fn get_as_items(&self, key: &str) -> Vec<Item> {
        for f in &self.fields_inner {
            if f.key == key {
                match &f.value_inner {
                    FieldValue::None_ => return Vec::new(),
                    FieldValue::Str(s) => {
                        if s.is_empty() {
                            return Vec::new();
                        }
                        return vec![Item {
                            key: String::new(),
                            value: s.clone(),
                        }];
                    }
                    FieldValue::Array(items) => return items.clone(),
                }
            }
        }
        Vec::new()
    }

    fn get_as_str(&self, key: &str) -> PyResult<String> {
        for f in &self.fields_inner {
            if f.key == key {
                match &f.value_inner {
                    FieldValue::None_ => return Ok(String::new()),
                    FieldValue::Str(s) => return Ok(s.clone()),
                    FieldValue::Array(_) => {
                        return Err(PyValueError::new_err(format!(
                            "value of {:?} is <class 'tuple'>, not str",
                            key
                        )));
                    }
                }
            }
        }
        Ok(String::new())
    }

    #[pyo3(signature = (key, value=None))]
    fn set(&self, key: &str, value: Option<&Bound<'_, pyo3::PyAny>>) -> PyResult<Self> {
        let fv = match value {
            None => FieldValue::None_,
            Some(obj) => {
                if obj.is_none() {
                    FieldValue::None_
                } else if let Ok(s) = obj.cast::<PyString>() {
                    FieldValue::Str(s.to_str()?.to_string())
                } else if let Ok(seq) = obj.cast::<PySequence>() {
                    let mut items = Vec::with_capacity(seq.len()?);
                    for i in 0..seq.len()? {
                        let item = seq.get_item(i)?;
                        items.push(item.extract::<Item>()?);
                    }
                    FieldValue::Array(items)
                } else {
                    FieldValue::from_py(obj)?
                }
            }
        };
        let new_field = Field {
            key: key.to_string(),
            value_inner: fv,
        };
        Ok(self.set_field(new_field))
    }

    fn index_of(&self, key: &str) -> usize {
        for (i, f) in self.fields_inner.iter().enumerate() {
            if f.key == key {
                return i;
            }
        }
        self.fields_inner.len()
    }

    fn set_or_insert(
        &self,
        key: &str,
        value: &Bound<'_, pyo3::PyAny>,
        index: usize,
    ) -> PyResult<Self> {
        if self.fields_inner.iter().any(|f| f.key == key) {
            return self.set(key, Some(value));
        }
        let fv = if value.is_none() {
            FieldValue::None_
        } else if let Ok(s) = value.cast::<PyString>() {
            FieldValue::Str(s.to_str()?.to_string())
        } else if let Ok(seq) = value.cast::<PySequence>() {
            let mut items = Vec::with_capacity(seq.len()?);
            for i in 0..seq.len()? {
                let item = seq.get_item(i)?;
                items.push(item.extract::<Item>()?);
            }
            FieldValue::Array(items)
        } else {
            FieldValue::from_py(value)?
        };
        let new_field = Field {
            key: key.to_string(),
            value_inner: fv,
        };
        let mut fields = self.fields_inner.clone();
        let idx = index.min(fields.len());
        fields.insert(idx, new_field);
        Ok(Wiki::make(self.r#type.clone(), fields, self._eol.clone()))
    }

    fn set_values(&self, values: &Bound<'_, PyDict>) -> PyResult<Self> {
        let mut w = self.clone();
        for (k, v) in values.iter() {
            let key: String = k.extract()?;
            let fv = FieldValue::from_py(&v)?;
            let new_field = Field {
                key,
                value_inner: fv,
            };
            w = w.set_field(new_field);
        }
        Ok(w)
    }

    fn remove(&self, key: &str) -> Self {
        let fields: Vec<Field> = self
            .fields_inner
            .iter()
            .filter(|f| f.key != key)
            .cloned()
            .collect();
        Wiki::make(self.r#type.clone(), fields, self._eol.clone())
    }

    fn semantically_equal(&self, other: &Wiki) -> bool {
        if self.r#type != other.r#type {
            return false;
        }
        if self.fields_inner.len() != other.fields_inner.len() {
            return false;
        }
        let mut a_sorted = self.fields_inner.clone();
        let mut b_sorted = other.fields_inner.clone();
        a_sorted.sort_by_key(field_sort_key);
        b_sorted.sort_by_key(field_sort_key);
        a_sorted
            .iter()
            .zip(b_sorted.iter())
            .all(|(a, b)| a.semantically_equal(b))
    }

    fn remove_duplicated_fields(&self, py: Python<'_>) -> PyResult<Self> {
        let mut fields_map: Vec<(String, FieldValue)> = Vec::new();
        let mut duplicated_keys: Vec<String> = Vec::new();

        for f in &self.fields_inner {
            if duplicated_keys.contains(&f.key) {
                continue;
            }
            if let Some(pos) = fields_map.iter().position(|(k, _)| k == &f.key) {
                if !f.value_inner.is_truthy() {
                    continue;
                }
                if !fields_map[pos].1.is_truthy() {
                    fields_map[pos].1 = f.value_inner.clone();
                } else if fields_map[pos].1 == f.value_inner {
                    continue;
                } else {
                    duplicated_keys.push(f.key.clone());
                }
            } else {
                fields_map.push((f.key.clone(), f.value_inner.clone()));
            }
        }

        if !duplicated_keys.is_empty() {
            duplicated_keys.sort();
            let exc_type: Bound<'_, PyType> =
                DuplicatedKeyError::type_object(py).cast().unwrap().clone();
            let err = PyErr::from_type(
                exc_type,
                format!("found duplicated keys {:?}", duplicated_keys),
            );
            let inst = err.value(py);
            inst.setattr("keys", duplicated_keys)?;
            return Err(err);
        }

        if fields_map.len() == self.fields_inner.len() {
            return Ok(self.clone());
        }

        let fields: Vec<Field> = fields_map
            .into_iter()
            .map(|(k, v)| Field {
                key: k,
                value_inner: v,
            })
            .collect();
        Ok(Wiki::make(self.r#type.clone(), fields, self._eol.clone()))
    }

    fn render(&self) -> String {
        render_impl(self)
    }
}

impl Wiki {
    fn set_field(&self, field: Field) -> Self {
        let mut fields = Vec::with_capacity(self.fields_inner.len());
        let mut found = false;
        for f in &self.fields_inner {
            if f.key != field.key {
                fields.push(f.clone());
                continue;
            }
            if found {
                continue;
            }
            fields.push(field.clone());
            found = true;
        }
        if !found {
            fields.push(field);
        }
        Wiki::make(self.r#type.clone(), fields, self._eol.clone())
    }
}

impl PartialEq for Field {
    fn eq(&self, other: &Self) -> bool {
        self.key == other.key && self.value_inner == other.value_inner
    }
}

fn field_sort_key(f: &Field) -> (String, i32) {
    (f.key.clone(), f.value_inner.emp_key())
}

// ─── parse ──────────────────────────────────────────────────────

const PREFIX: &str = "{{Infobox";
const SUFFIX: &str = "}}";

#[pyfunction]
fn parse(py: Python<'_>, s: &str) -> PyResult<Wiki> {
    let (s_owned, eol) = normalize_eol(s);
    let s = &s_owned;

    let stripped_start = s.len() - s.trim_start().len();
    let line_offset = 1 + s[..stripped_start].matches('\n').count();
    let s = s.trim();

    if s.is_empty() {
        return Ok(Wiki::make(None, Vec::new(), eol));
    }

    if !s.starts_with(PREFIX) {
        return raise_global_prefix(py);
    }
    if !s.ends_with(SUFFIX) {
        return raise_global_suffix(py);
    }

    let bytes = s.as_bytes();
    let slen = s.len();

    let first_nl = memchr(b'\n', bytes);
    if first_nl.is_none() {
        let wiki_type = s[9..slen - 2].trim().to_string();
        return Ok(Wiki::make(Some(wiki_type), Vec::new(), eol));
    }
    let first_nl = first_nl.unwrap();
    let wiki_type = s[9..first_nl].trim().to_string();

    let last_nl = memrchr(b'\n', bytes);
    let last_nl = last_nl.unwrap();
    if first_nl >= last_nl {
        return Ok(Wiki::make(Some(wiki_type), Vec::new(), eol));
    }

    let mut fields: Vec<Field> = Vec::new();
    let mut item_container: Vec<Item> = Vec::new();
    let mut in_array = false;
    let mut current_key = String::new();

    let mut pos = first_nl + 1;
    let mut body_lino: usize = 0;

    while pos < last_nl {
        // Find next newline
        let nl = match memchr(b'\n', &bytes[pos..last_nl]) {
            Some(offset) => pos + offset,
            None => last_nl,
        };

        let line_raw = &s[pos..nl];
        pos = nl + 1;

        let lino = body_lino + line_offset;
        body_lino += 1;

        let line = line_raw.trim();
        if line.is_empty() {
            continue;
        }

        let first_byte = line.as_bytes()[0];

        if first_byte == b'|' {
            if in_array {
                return raise_array_no_close(py, Some(lino), Some(line));
            }
            current_key.clear();

            let eq_pos = match line[1..].find('=') {
                Some(p) => p + 1,
                None => return raise_expecting_sign_equal(py, Some(lino), Some(line)),
            };

            let key = line[1..eq_pos].trim().to_string();
            let value = line[eq_pos + 1..].trim_start();

            if value.is_empty() {
                fields.push(Field {
                    key,
                    value_inner: FieldValue::None_,
                });
                continue;
            }
            if value == "{" {
                in_array = true;
                current_key = key;
                continue;
            }
            fields.push(Field {
                key,
                value_inner: FieldValue::Str(value.to_string()),
            });
            continue;
        }

        if !in_array {
            return raise_expecting_new_field(py, Some(lino), Some(line));
        }

        if line == "}" {
            in_array = false;
            fields.push(Field {
                key: std::mem::take(&mut current_key),
                value_inner: FieldValue::Array(std::mem::take(&mut item_container)),
            });
            continue;
        }

        let line_bytes = line.as_bytes();
        if first_byte != b'[' || *line_bytes.last().unwrap() != b']' {
            return raise_invalid_array_item(py, Some(lino), Some(line));
        }

        let inner = &line[1..line.len() - 1];
        if let Some(pipe) = inner.find('|') {
            item_container.push(Item {
                key: inner[..pipe].trim().to_string(),
                value: inner[pipe + 1..].trim().to_string(),
            });
        } else {
            item_container.push(Item {
                key: String::new(),
                value: inner.trim().to_string(),
            });
        }
    }

    if in_array {
        let lines: Vec<&str> = s.lines().collect();
        let last_line = if lines.len() >= 2 {
            lines[lines.len() - 2]
        } else {
            ""
        };
        return raise_array_no_close(
            py,
            Some(s.matches('\n').count() + line_offset),
            Some(last_line),
        );
    }

    Ok(Wiki::make(Some(wiki_type), fields, eol))
}

fn normalize_eol(s: &str) -> (String, String) {
    if !s.contains('\r') {
        return (s.to_string(), "\n".to_string());
    }
    let crlf = s.matches("\r\n").count();
    let all_lf = s.matches('\n').count();
    let lf = all_lf - crlf;
    let eol = if crlf >= lf {
        "\r\n".to_string()
    } else {
        "\n".to_string()
    };
    let mut result = s.replace("\r\n", "\n");
    if result.contains('\r') {
        result = result.replace('\r', "\n");
    }
    (result, eol)
}

#[inline]
fn memchr(needle: u8, haystack: &[u8]) -> Option<usize> {
    haystack.iter().position(|&b| b == needle)
}

#[inline]
fn memrchr(needle: u8, haystack: &[u8]) -> Option<usize> {
    haystack.iter().rposition(|&b| b == needle)
}

// ─── try_parse ──────────────────────────────────────────────────

#[pyfunction]
fn try_parse(py: Python<'_>, s: &str) -> PyResult<Wiki> {
    match parse(py, s) {
        Ok(w) => Ok(w),
        Err(e) => {
            if e.is_instance_of::<WikiSyntaxError>(py) {
                Ok(Wiki::make(None, Vec::new(), "\n".to_string()))
            } else {
                Err(e)
            }
        }
    }
}

// ─── render ─────────────────────────────────────────────────────

fn render_impl(w: &Wiki) -> String {
    let mut parts: Vec<String> = Vec::new();

    match &w.r#type {
        Some(t) if !t.is_empty() => parts.push(format!("{{{{Infobox {t}")),
        _ => parts.push("{{Infobox".to_string()),
    }

    for f in &w.fields_inner {
        match &f.value_inner {
            FieldValue::Str(s) => {
                parts.push(format!("|{}= {}", f.key, s));
            }
            FieldValue::Array(items) => {
                parts.push(format!("|{}={{{{", f.key));
                for item in items {
                    if !item.key.is_empty() {
                        parts.push(format!("[{}|{}]", item.key, item.value));
                    } else {
                        parts.push(format!("[{}]", item.value));
                    }
                }
                parts.push("}".to_string());
            }
            FieldValue::None_ => {
                parts.push(format!("|{}= ", f.key));
            }
        }
    }

    parts.push("}}".to_string());
    parts.join(&w._eol)
}

#[pyfunction]
fn render(w: &Wiki) -> String {
    render_impl(w)
}

// ─── read_type / read_array_item / read_start_line ──────────────

#[pyfunction]
fn read_type(s: &str) -> String {
    let end = s.find('\n').or_else(|| s.find('}')).unwrap_or(s.len());
    s[9..end].trim().to_string()
}

#[pyfunction]
fn read_array_item(py: Python<'_>, line: &str, lino: usize) -> PyResult<(String, String)> {
    let bytes = line.as_bytes();
    if bytes.first() != Some(&b'[') || bytes.last() != Some(&b']') {
        return raise_invalid_array_item(py, Some(lino), Some(line));
    }
    let inner = &line[1..line.len() - 1];
    if let Some(pipe) = inner.find('|') {
        Ok((
            inner[..pipe].trim().to_string(),
            inner[pipe + 1..].trim().to_string(),
        ))
    } else {
        Ok((String::new(), inner.trim().to_string()))
    }
}

#[pyfunction]
fn read_start_line(py: Python<'_>, line: &str, lino: usize) -> PyResult<(String, String)> {
    let trimmed = line[1..].trim();
    match trimmed.find('=') {
        Some(eq) => Ok((
            trimmed[..eq].trim_end().to_string(),
            trimmed[eq + 1..].trim_start().to_string(),
        )),
        None => raise_expecting_sign_equal(py, Some(lino), Some(line)),
    }
}

// ─── Module ─────────────────────────────────────────────────────

#[pymodule]
fn bgm_tv_wiki(py: Python<'_>, m: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
    m.add_class::<Item>()?;
    m.add_class::<Field>()?;
    m.add_class::<Wiki>()?;
    m.add_function(wrap_pyfunction!(parse, m)?)?;
    m.add_function(wrap_pyfunction!(render, m)?)?;
    m.add_function(wrap_pyfunction!(try_parse, m)?)?;
    m.add_function(wrap_pyfunction!(read_type, m)?)?;
    m.add_function(wrap_pyfunction!(read_array_item, m)?)?;
    m.add_function(wrap_pyfunction!(read_start_line, m)?)?;
    m.add("WikiSyntaxError", py.get_type::<WikiSyntaxError>())?;
    m.add("GlobalPrefixError", py.get_type::<GlobalPrefixError>())?;
    m.add("GlobalSuffixError", py.get_type::<GlobalSuffixError>())?;
    m.add("ArrayNoCloseError", py.get_type::<ArrayNoCloseError>())?;
    m.add(
        "InvalidArrayItemError",
        py.get_type::<InvalidArrayItemError>(),
    )?;
    m.add(
        "ExpectingNewFieldError",
        py.get_type::<ExpectingNewFieldError>(),
    )?;
    m.add(
        "ExpectingSignEqualError",
        py.get_type::<ExpectingSignEqualError>(),
    )?;
    m.add("DuplicatedKeyError", py.get_type::<DuplicatedKeyError>())?;
    // Type aliases (just object)
    let builtins = py.import("builtins")?;
    let obj = builtins.getattr("object")?;
    m.add("ValueType", &obj)?;
    m.add("ValueInputType", &obj)?;
    Ok(())
}
