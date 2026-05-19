import { useCallback, useSyncExternalStore } from "react";
import { Button } from "../../ui/Button";
import {
  hideSocialBanterInTranscript,
  setHideSocialBanterInTranscript,
} from "../../lib/parse";

function subscribeBanterFilter(cb: () => void) {
  const onStorage = (e: StorageEvent) => {
    if (
      e.key === "altrasia.hideSocialBanterInTranscript" ||
      e.key === "altrasia.showSocialIdleInTranscript"
    ) {
      cb();
    }
  };
  window.addEventListener("storage", onStorage);
  window.addEventListener("altrasia-banter-filter", cb);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener("altrasia-banter-filter", cb);
  };
}

export function notifyBanterFilterChanged() {
  window.dispatchEvent(new Event("altrasia-banter-filter"));
}

type Props = {
  visible: boolean;
};

export function BanterTranscriptToggle({ visible }: Props) {
  const hidden = useSyncExternalStore(
    subscribeBanterFilter,
    hideSocialBanterInTranscript,
    () => false
  );

  const toggle = useCallback(() => {
    setHideSocialBanterInTranscript(!hidden);
    notifyBanterFilterChanged();
  }, [hidden]);

  if (!visible) return null;

  return (
    <Button
      type="button"
      variant={hidden ? "ghost" : "secondary"}
      size="sm"
      className="banter-transcript-toggle"
      onClick={toggle}
      aria-pressed={!hidden}
      data-testid="banter-transcript-toggle"
      title={
        hidden
          ? "Show sidebar banter in the chronicle"
          : "Hide sidebar banter from the chronicle"
      }
    >
      {hidden ? "Show banter" : "Hide banter"}
    </Button>
  );
}
