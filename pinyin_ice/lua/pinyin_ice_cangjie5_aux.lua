local M = {}

local PROP_CODE = "pinyin_ice_cangjie5_aux_code"
local PROP_BASE = "pinyin_ice_cangjie5_aux_base"
local PROP_SEPARATOR = "pinyin_ice_cangjie5_aux_separator"
local TARGET_EDGE = "last"
local SEPARATORS = {
  [";"] = ";",
  semicolon = ";",
  [","] = ",",
  comma = ",",
}

local function get_prop(ctx, key)
  return ctx:get_property(key) or ""
end

local function set_state(ctx, code, base, separator)
  ctx:set_property(PROP_CODE, code or "")
  ctx:set_property(PROP_BASE, base or "")
  ctx:set_property(PROP_SEPARATOR, separator or "")
end

local function clear_state(ctx)
  set_state(ctx, "", "", "")
end

local function active_aux(ctx)
  local code = get_prop(ctx, PROP_CODE)
  local base = get_prop(ctx, PROP_BASE)
  local separator = get_prop(ctx, PROP_SEPARATOR)
  return code, base, separator
end

local function last_utf8_char(text)
  return text:match("([%z\1-\127\194-\244][\128-\191]*)$") or ""
end

local function first_utf8_char(text)
  return text:match("^([%z\1-\127\194-\244][\128-\191]*)") or ""
end

local function target_char(text)
  -- 分隔符接在拼音串末尾时，更自然的解释是拿辅助码筛候选词的末字。
  -- 如果你更想改成筛首字，把 TARGET_EDGE 改成 "first" 即可。
  if TARGET_EDGE == "first" then
    return first_utf8_char(text)
  end
  return last_utf8_char(text)
end

local function split_codes(code_string)
  local codes = {}
  for code in (code_string or ""):gmatch("[a-z]+") do
    if not code:match("^[xz]") then
      table.insert(codes, code)
    end
  end
  return codes
end

local function code_matches(aux, code)
  local key = (aux or ""):sub(1, 2)
  if key == "" then
    return true
  end
  if #key == 1 then
    return code:sub(1, 1) == key
  end
  return #code >= 1 and (code:sub(1, 1) .. code:sub(-1)) == key
end

local function sync_prompt(ctx)
  if not ctx then
    return
  end
  local composition = ctx.composition
  if not composition or composition:empty() then
    return
  end
  local aux, base, separator = active_aux(ctx)
  local segment = composition:back()
  if not segment then
    return
  end
  if base ~= "" then
    segment.prompt = (separator ~= "" and separator or ";") .. aux
  else
    segment.prompt = ""
  end
end

local function processor_init(env)
  local ctx = env.engine.context
  env.update_conn = ctx.update_notifier:connect(function(context)
    local _, base = active_aux(context)
    if context.input == "" then
      clear_state(context)
      sync_prompt(context)
      return
    end
    if base ~= "" and context.input ~= base then
      clear_state(context)
      sync_prompt(context)
    end
  end)
  env.commit_conn = ctx.commit_notifier:connect(function(context)
    clear_state(context)
  end)
  env.delete_conn = ctx.delete_notifier:connect(function(context)
    if context.input == "" then
      clear_state(context)
    end
  end)
end

local function processor_fini(env)
  if env.update_conn then
    env.update_conn:disconnect()
  end
  if env.commit_conn then
    env.commit_conn:disconnect()
  end
  if env.delete_conn then
    env.delete_conn:disconnect()
  end
end

local function refresh_menu(ctx)
  if ctx and ctx:is_composing() then
    ctx:refresh_non_confirmed_composition()
  end
  sync_prompt(ctx)
end

local function processor_func(key, env)
  local ctx = env.engine.context
  local aux, base, separator = active_aux(ctx)
  local repr = key:repr()
  local typed_separator = SEPARATORS[repr]

  if typed_separator and ctx:is_composing() and base == "" then
    set_state(ctx, "", ctx.input or "", typed_separator)
    refresh_menu(ctx)
    return 1
  end

  if base ~= "" then
    if typed_separator then
      refresh_menu(ctx)
      return 1
    end

    if repr == "BackSpace" then
      if aux ~= "" then
        set_state(ctx, aux:sub(1, -2), base, separator)
      else
        clear_state(ctx)
      end
      refresh_menu(ctx)
      return 1
    end

    if #repr == 1 and repr:match("^[a-z]$") then
      if #aux < 2 then
        set_state(ctx, aux .. repr, base, separator)
        refresh_menu(ctx)
      end
      return 1
    end

    if repr == "Escape" then
      clear_state(ctx)
      refresh_menu(ctx)
    end
  end

  return 2
end

local function filter_func(input, env)
  local ctx = env.engine.context
  local aux, base = active_aux(ctx)

  if base ~= "" and ctx.input ~= "" and ctx.input ~= base then
    clear_state(ctx)
    aux = ""
    sync_prompt(ctx)
  end

  if aux == "" then
    for cand in input:iter() do
      yield(cand)
    end
    return
  end

  local reverse = env.reverse or ReverseLookup("cangjie5")
  env.reverse = reverse

  for cand in input:iter() do
    local char = target_char(cand.text)
    local matched = false
    if char ~= "" then
      for _, code in ipairs(split_codes(reverse:lookup(char))) do
        if code_matches(aux, code) then
          matched = true
          break
        end
      end
    end
    if matched then
      yield(cand)
    end
  end
end

M.processor = {
  init = processor_init,
  func = processor_func,
  fini = processor_fini,
}

M.filter = {
  func = filter_func,
}

return M
