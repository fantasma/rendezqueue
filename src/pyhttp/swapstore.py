MAX_TTL_SECONDS = 20


class SwapStore:
  def __init__(self):
    # key -> {id, values, expiry}
    # If expiry is 0, this is not an actual entry.
    self.unmatched_offer_map = {}
    # key -> id -> {original_values, values, expiry}
    self.swapped_answer_multimap = {}

    self.ttl = MAX_TTL_SECONDS

  def print_unmatched(self):
    print(self.unmatched_offer_map)

  def print_swapped(self):
    print(self.swapped_answer_multimap)

  # Presumably, data was exchanged.
  def expire_swapped_answers(self, key, now_ms):
    expiring_answers = []
    answer_map = self.swapped_answer_multimap.get(key)
    if not answer_map:
      return True
    for id, v in answer_map.items():
      if v["expiry_ms"] > now_ms:
        break
      expiring_answers.append(id)
    if len(expiring_answers) == len(answer_map):
      del self.swapped_answer_multimap[key]
      return True

    for id in expiring_answers:
      del answer_map[id]
    return False

  # No takers.
  def expire_unmatched_offers(self, now_ms):
    expiring_offers = []
    for key, v in list(self.unmatched_offer_map.items()):
      if v["expiry_ms"] > now_ms:
        break
      if not self.expire_swapped_answers(key, now_ms):
        break
      expiring_offers.append(key)
    for key in expiring_offers:
      del self.unmatched_offer_map[key]

  @staticmethod
  def matches_original(original_values, offset, values):
    if len(original_values) < offset:
      return False  # Too far ahead. Out of place.
    if len(original_values) > offset + len(values):
      return False  # Too short. Out
    original_slice = original_values[offset:]
    return all(v == values[i] for i, v in enumerate(original_slice))

  def tryswap(self, key, id, offset, values, now_ms, ttl=0):
    if not isinstance(now_ms, int):
      return 500
    self.expire_unmatched_offers(now_ms)

    answer_map = self.swapped_answer_multimap.get(key)
    if ttl == 0 or ttl > self.ttl:
      ttl = self.ttl

    if answer_map:
      answer = answer_map.get(id)
      if answer:
        if SwapStore.matches_original(answer["original_values"], offset, values):
          return {
            "key": key,
            "id": id,
            "offset": len(answer["original_values"]),
            "values": answer["values"],
          }
        return 404

    # Reached this line? No answer.
    offer = self.unmatched_offer_map.get(key)
    if offer and offer["expiry_ms"] == 0:
      del self.unmatched_offer_map[key]
      offer = None  # Fall through to next case.
      self.expire_swapped_answers(key, now_ms)  # Ensure stuff would expire.

    # We'll need to make an offer.
    if not offer:
      if offset != 0:
        return 404
      if len(values) > 0:
        self.unmatched_offer_map[key] = {
          "id": id,
          "values": values,
          "expiry_ms": now_ms + ttl * 1000,
        }
      return {
        "key": key,
        "id": id,
        "offset": len(values),
        "ttl": ttl,
      }

    # Still no match? Might as well reset expiry.
    if offer["id"] == id:
      original_values = offer["values"]
      if SwapStore.matches_original(original_values, offset, values):
        del self.unmatched_offer_map[key]
        self.unmatched_offer_map[key] = {
          "id": id,
          "values": original_values[:offset] + values,
          "expiry_ms": now_ms + ttl * 1000,
        }
        return {
          "key": key,
          "id": id,
          "offset": offset + len(values),
          "ttl": ttl,
        }
      return 404
    # Reached this line? Got a match!

    if offset != 0:
      # Invalid offset. We had no existing data!
      return 404

    if not answer_map:
      answer_map = {}
      self.swapped_answer_multimap[key] = answer_map
    answer_map[id] = {
      "original_values": values,
      "values": offer["values"],
      "expiry_ms": now_ms + ttl * 1000,
    }
    answer_map[offer["id"]] = {
      "original_values": offer["values"],
      "values": values,
      "expiry_ms": now_ms + ttl * 1000,
    }
    del self.unmatched_offer_map[key]
    self.unmatched_offer_map[key] = {
      "expiry_ms": 0,
    }
    return {
      "key": key,
      "id": id,
      "offset": len(values),
      "values": offer["values"],
    }
