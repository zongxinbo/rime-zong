local M = {}

local kNoop = 2

function M.init(env)
  local config = env.engine.schema.config
  env.max_code_length = config:get_int("speller/max_code_length") or 4
  env.commit_suffixes = config:get_string("lingcang_auto_select/commit_suffixes") or "aeiou"
end

local function is_plain_letter(key_event)
  if key_event:release() or key_event:alt() or key_event:ctrl() or key_event:shift() or key_event:caps() then
    return false
  end
  return key_event.keycode >= ("a"):byte() and key_event.keycode <= ("z"):byte()
end

local function ends_with_commit_suffix(input, suffixes)
  if input == "" then
    return false
  end
  return suffixes:find(input:sub(-1), 1, true) ~= nil
end

function M.func(key_event, env)
  if not is_plain_letter(key_event) then
    return kNoop
  end

  local context = env.engine.context
  local input = context.input
  if input == "" then
    return kNoop
  end

  if #input >= env.max_code_length or ends_with_commit_suffix(input, env.commit_suffixes) then
    local segment = context.composition:toSegmentation():back()
    if not segment then
      return kNoop
    end
    if segment:get_candidate_at(0) then
      env.engine:process_key(KeyEvent("1"))
    end
  end

  return kNoop
end

return M
