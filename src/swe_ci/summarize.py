if __name__ == "__main__":

    import json
    from swe_ci.benchmark import summarize

    summary = summarize()

    res = {
        "score": summary[0]["metrics"]["EvoScore(gamma=1)"],
        "reason": summary[0]["iterations"]
    }

    with open("./summary.json", "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=4)
